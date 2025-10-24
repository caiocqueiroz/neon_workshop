import os
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.corecode.models import StudentClass

from .models import Student, StudentBulkUpload


class StudentBulkUploadTestCase(TestCase):
    """Tests for student bulk upload signal handlers"""

    def test_bulk_upload_creates_students_from_valid_csv(self):
        """Test that bulk upload creates students from valid CSV"""
        csv_content = b"""registration_number,surname,firstname,gender,current_class
001,Doe,John,male,Grade 1
002,Smith,Jane,female,Grade 1"""

        csv_file = SimpleUploadedFile(
            "students.csv", csv_content, content_type="text/csv"
        )

        bulk_upload = StudentBulkUpload.objects.create(csv_file=csv_file)

        # Verify that students were created
        self.assertEqual(Student.objects.count(), 2)
        self.assertTrue(Student.objects.filter(registration_number="001").exists())
        self.assertTrue(Student.objects.filter(registration_number="002").exists())

        student1 = Student.objects.get(registration_number="001")
        self.assertEqual(student1.firstname, "John")
        self.assertEqual(student1.surname, "Doe")
        self.assertEqual(student1.gender, "male")
        self.assertEqual(student1.current_class.name, "Grade 1")

        # Verify that bulk upload was deleted after processing
        self.assertFalse(StudentBulkUpload.objects.filter(id=bulk_upload.id).exists())

    def test_bulk_upload_creates_class_if_not_exists(self):
        """Test that bulk upload creates class automatically if it doesn't exist"""
        csv_content = b"""registration_number,surname,firstname,gender,current_class
001,Doe,John,male,Grade 5"""

        csv_file = SimpleUploadedFile(
            "students.csv", csv_content, content_type="text/csv"
        )

        # Verify class doesn't exist yet
        self.assertFalse(StudentClass.objects.filter(name="Grade 5").exists())

        StudentBulkUpload.objects.create(csv_file=csv_file)

        # Verify class was created
        self.assertTrue(StudentClass.objects.filter(name="Grade 5").exists())

        student = Student.objects.get(registration_number="001")
        self.assertEqual(student.current_class.name, "Grade 5")

    def test_bulk_upload_skips_duplicate_registration_numbers(self):
        """Test that bulk upload prevents duplicate registration numbers"""
        # Create existing student
        student_class = StudentClass.objects.create(name="Grade 1")
        Student.objects.create(
            registration_number="001",
            firstname="Existing",
            surname="Student",
            current_class=student_class,
        )

        csv_content = b"""registration_number,surname,firstname,gender,current_class
001,Doe,John,male,Grade 1
002,Smith,Jane,female,Grade 1"""

        csv_file = SimpleUploadedFile(
            "students.csv", csv_content, content_type="text/csv"
        )

        StudentBulkUpload.objects.create(csv_file=csv_file)

        # Should have 2 students total (1 existing + 1 new)
        self.assertEqual(Student.objects.count(), 2)

        # The existing student should not be overwritten
        student = Student.objects.get(registration_number="001")
        self.assertEqual(student.firstname, "Existing")
        self.assertEqual(student.surname, "Student")

    def test_bulk_upload_handles_optional_fields(self):
        """Test that bulk upload handles optional fields correctly"""
        csv_content = b"""registration_number,surname,firstname,other_names,gender,parent_number,address,current_class
001,Doe,John,Michael,male,1234567890,123 Main St,Grade 1"""

        csv_file = SimpleUploadedFile(
            "students.csv", csv_content, content_type="text/csv"
        )

        StudentBulkUpload.objects.create(csv_file=csv_file)

        student = Student.objects.get(registration_number="001")
        self.assertEqual(student.other_name, "Michael")
        self.assertEqual(student.parent_mobile_number, "1234567890")
        self.assertEqual(student.address, "123 Main St")

    def test_bulk_upload_handles_missing_optional_fields(self):
        """Test that bulk upload handles missing optional fields"""
        csv_content = b"""registration_number,surname,firstname,gender,current_class
001,Doe,John,male,Grade 1"""

        csv_file = SimpleUploadedFile(
            "students.csv", csv_content, content_type="text/csv"
        )

        StudentBulkUpload.objects.create(csv_file=csv_file)

        student = Student.objects.get(registration_number="001")
        self.assertEqual(student.other_name, "")
        self.assertEqual(student.parent_mobile_number, "")
        self.assertEqual(student.address, "")

    def test_bulk_upload_skips_rows_without_registration_number(self):
        """Test that bulk upload skips rows without registration number"""
        csv_content = b"""registration_number,surname,firstname,gender,current_class
,Doe,John,male,Grade 1
002,Smith,Jane,female,Grade 1"""

        csv_file = SimpleUploadedFile(
            "students.csv", csv_content, content_type="text/csv"
        )

        StudentBulkUpload.objects.create(csv_file=csv_file)

        # Should only create one student (002)
        self.assertEqual(Student.objects.count(), 1)
        self.assertTrue(Student.objects.filter(registration_number="002").exists())

    def test_bulk_upload_handles_lowercase_gender(self):
        """Test that bulk upload converts gender to lowercase"""
        csv_content = b"""registration_number,surname,firstname,gender,current_class
001,Doe,John,MALE,Grade 1
002,Smith,Jane,Female,Grade 1"""

        csv_file = SimpleUploadedFile(
            "students.csv", csv_content, content_type="text/csv"
        )

        StudentBulkUpload.objects.create(csv_file=csv_file)

        student1 = Student.objects.get(registration_number="001")
        student2 = Student.objects.get(registration_number="002")
        self.assertEqual(student1.gender, "male")
        self.assertEqual(student2.gender, "female")

    def test_bulk_upload_sets_status_to_active(self):
        """Test that bulk upload sets current_status to active"""
        csv_content = b"""registration_number,surname,firstname,gender,current_class
001,Doe,John,male,Grade 1"""

        csv_file = SimpleUploadedFile(
            "students.csv", csv_content, content_type="text/csv"
        )

        StudentBulkUpload.objects.create(csv_file=csv_file)

        student = Student.objects.get(registration_number="001")
        self.assertEqual(student.current_status, "active")


class StudentDeletionTestCase(TestCase):
    """Tests for student deletion signal handlers"""

    def test_passport_deleted_when_student_deleted(self):
        """Test that passport file is deleted when student is deleted"""
        student_class = StudentClass.objects.create(name="Grade 1")

        # Create a fake image file
        fake_image = BytesIO(b"fake image content")
        fake_image.name = "test_passport.jpg"
        passport_file = SimpleUploadedFile(
            "test_passport.jpg",
            fake_image.getvalue(),
            content_type="image/jpeg",
        )

        student = Student.objects.create(
            registration_number="001",
            firstname="John",
            surname="Doe",
            current_class=student_class,
            passport=passport_file,
        )

        passport_path = student.passport.path

        # Verify file exists
        self.assertTrue(os.path.exists(passport_path))

        # Delete student
        student.delete()

        # Verify file was deleted
        self.assertFalse(os.path.exists(passport_path))

    def test_student_without_passport_can_be_deleted(self):
        """Test that student without passport can be deleted without error"""
        student_class = StudentClass.objects.create(name="Grade 1")
        student = Student.objects.create(
            registration_number="001",
            firstname="John",
            surname="Doe",
            current_class=student_class,
        )

        # Should not raise any exception
        student.delete()

        # Verify student was deleted
        self.assertFalse(Student.objects.filter(registration_number="001").exists())


class StudentModelTestCase(TestCase):
    """Tests for student model methods"""

    def test_student_str_representation(self):
        """Test student string representation"""
        student_class = StudentClass.objects.create(name="Grade 1")
        student = Student.objects.create(
            registration_number="001",
            firstname="John",
            surname="Doe",
            other_name="Michael",
            current_class=student_class,
        )

        expected = "Doe John Michael (001)"
        self.assertEqual(str(student), expected)

    def test_student_get_absolute_url(self):
        """Test student get_absolute_url method"""
        student_class = StudentClass.objects.create(name="Grade 1")
        student = Student.objects.create(
            registration_number="001",
            firstname="John",
            surname="Doe",
            current_class=student_class,
        )

        expected_url = f"/student/{student.pk}/"
        self.assertEqual(student.get_absolute_url(), expected_url)
