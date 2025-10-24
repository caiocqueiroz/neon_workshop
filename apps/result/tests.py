from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass, Subject
from apps.students.models import Student

from .models import Result
from .views import ResultListView


class ResultCreateViewTestCase(TestCase):
    """Tests for create_result view"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.session = AcademicSession.objects.create(name="2024/2025", current=True)
        self.term = AcademicTerm.objects.create(name="First Term", current=True)
        self.student_class = StudentClass.objects.create(name="Grade 1")
        self.subject1 = Subject.objects.create(name="Mathematics-Create")
        self.subject2 = Subject.objects.create(name="English-Create")
        self.student1 = Student.objects.create(
            registration_number="001",
            firstname="John",
            surname="Doe",
            current_class=self.student_class,
        )
        self.student2 = Student.objects.create(
            registration_number="002",
            firstname="Jane",
            surname="Smith",
            current_class=self.student_class,
        )

    def test_create_result_requires_login(self):
        """Test that create result view requires authentication"""
        response = self.client.get(reverse("create-result"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_create_result_get_shows_student_list(self):
        """Test that GET request shows student list"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("create-result"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("students", response.context)
        self.assertContains(response, "John")
        self.assertContains(response, "Jane")

    def test_create_result_step1_post_with_students(self):
        """Test POST with student selection proceeds to step 2"""
        self.client.login(username="testuser", password="testpass123")

        # Use middleware to add current_session and current_term to request
        session = self.client.session
        session["_auth_user_id"] = self.user.id
        session.save()

        response = self.client.post(
            reverse("create-result"),
            {"students": [self.student1.id, self.student2.id]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertIn("students", response.context)
        self.assertIn("count", response.context)
        self.assertEqual(response.context["count"], 2)

    def test_create_result_post_without_students_shows_warning(self):
        """Test POST without student selection shows warning"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("create-result"), {})
        self.assertEqual(response.status_code, 200)
        messages = list(response.context["messages"])
        self.assertTrue(any("didnt select any student" in str(m) for m in messages))

    def test_create_result_final_step_creates_results(self):
        """Test final step creates results for selected students and subjects"""
        self.client.login(username="testuser", password="testpass123")

        student_ids = f"{self.student1.id},{self.student2.id}"
        response = self.client.post(
            reverse("create-result"),
            {
                "finish": "true",
                "session": self.session.id,
                "term": self.term.id,
                "subjects": [self.subject1.id, self.subject2.id],
                "students": student_ids,
            },
        )

        # Should redirect to edit-results
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("edit-results"))

        # Verify results were created
        # 2 students × 2 subjects = 4 results
        self.assertEqual(Result.objects.count(), 4)

        # Verify specific results
        result1 = Result.objects.filter(
            student=self.student1, subject=self.subject1
        ).first()
        self.assertIsNotNone(result1)
        self.assertEqual(result1.session, self.session)
        self.assertEqual(result1.term, self.term)
        self.assertEqual(result1.current_class, self.student_class)

    def test_create_result_prevents_duplicate_results(self):
        """Test that duplicate results are not created"""
        self.client.login(username="testuser", password="testpass123")

        # Create existing result
        Result.objects.create(
            student=self.student1,
            session=self.session,
            term=self.term,
            current_class=self.student_class,
            subject=self.subject1,
        )

        student_ids = f"{self.student1.id}"
        response = self.client.post(
            reverse("create-result"),
            {
                "finish": "true",
                "session": self.session.id,
                "term": self.term.id,
                "subjects": [self.subject1.id],
                "students": student_ids,
            },
        )

        # Should not create duplicate
        self.assertEqual(Result.objects.count(), 1)

    def test_create_result_skips_students_without_class(self):
        """Test that students without current_class are skipped"""
        self.client.login(username="testuser", password="testpass123")

        student_no_class = Student.objects.create(
            registration_number="003",
            firstname="No",
            surname="Class",
            current_class=None,
        )

        student_ids = f"{self.student1.id},{student_no_class.id}"
        response = self.client.post(
            reverse("create-result"),
            {
                "finish": "true",
                "session": self.session.id,
                "term": self.term.id,
                "subjects": [self.subject1.id],
                "students": student_ids,
            },
        )

        # Should only create result for student1
        self.assertEqual(Result.objects.count(), 1)
        self.assertTrue(Result.objects.filter(student=self.student1).exists())
        self.assertFalse(Result.objects.filter(student=student_no_class).exists())


class ResultEditViewTestCase(TestCase):
    """Tests for edit_results view"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.session = AcademicSession.objects.create(name="2024/2025", current=True)
        self.term = AcademicTerm.objects.create(name="First Term", current=True)
        self.student_class = StudentClass.objects.create(name="Grade 1 Edit")
        self.subject = Subject.objects.create(name="Mathematics-Edit")
        self.student = Student.objects.create(
            registration_number="001-edit",
            firstname="John",
            surname="Doe",
            current_class=self.student_class,
        )
        self.result = Result.objects.create(
            student=self.student,
            session=self.session,
            term=self.term,
            current_class=self.student_class,
            subject=self.subject,
            test_score=0,
            exam_score=0,
        )

    def test_edit_results_requires_login(self):
        """Test that edit results view requires authentication"""
        response = self.client.get(reverse("edit-results"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_edit_results_get_shows_formset(self):
        """Test that GET request shows formset with current results"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("edit-results"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("formset", response.context)

    def test_edit_results_post_updates_scores(self):
        """Test that POST request updates result scores"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            reverse("edit-results"),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "1",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": self.result.id,
                "form-0-test_score": "80",
                "form-0-exam_score": "90",
            },
        )

        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("edit-results"))

        # Verify scores were updated
        self.result.refresh_from_db()
        self.assertEqual(self.result.test_score, 80)
        self.assertEqual(self.result.exam_score, 90)

    def test_edit_results_shows_success_message(self):
        """Test that successful update shows success message"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            reverse("edit-results"),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "1",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": self.result.id,
                "form-0-test_score": "80",
                "form-0-exam_score": "90",
            },
            follow=True,
        )

        messages = list(response.context["messages"])
        self.assertTrue(any("successfully updated" in str(m).lower() for m in messages))


class ResultListViewTestCase(TestCase):
    """Tests for ResultListView"""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.session = AcademicSession.objects.create(name="2024/2025", current=True)
        self.term = AcademicTerm.objects.create(name="First Term", current=True)
        self.student_class = StudentClass.objects.create(name="Grade 1 List")
        self.subject1 = Subject.objects.create(name="Mathematics-List")
        self.subject2 = Subject.objects.create(name="English-List")
        self.student1 = Student.objects.create(
            registration_number="001-list",
            firstname="John",
            surname="Doe",
            current_class=self.student_class,
        )
        self.student2 = Student.objects.create(
            registration_number="002-list",
            firstname="Jane",
            surname="Smith",
            current_class=self.student_class,
        )

    def test_result_list_view_requires_login(self):
        """Test that result list view requires authentication"""
        response = self.client.get(reverse("view-results"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_result_list_view_calculates_totals(self):
        """Test that result list view calculates test and exam totals"""
        # Create results for student1
        Result.objects.create(
            student=self.student1,
            session=self.session,
            term=self.term,
            current_class=self.student_class,
            subject=self.subject1,
            test_score=40,
            exam_score=60,
        )
        Result.objects.create(
            student=self.student1,
            session=self.session,
            term=self.term,
            current_class=self.student_class,
            subject=self.subject2,
            test_score=35,
            exam_score=55,
        )

        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("view-results"))
        self.assertEqual(response.status_code, 200)

        results = response.context["results"]
        self.assertIn(self.student1.id, results)

        student_result = results[self.student1.id]
        self.assertEqual(student_result["test_total"], 75)  # 40 + 35
        self.assertEqual(student_result["exam_total"], 115)  # 60 + 55
        self.assertEqual(student_result["total_total"], 190)  # 75 + 115

    def test_result_list_view_groups_by_student(self):
        """Test that results are grouped by student"""
        Result.objects.create(
            student=self.student1,
            session=self.session,
            term=self.term,
            current_class=self.student_class,
            subject=self.subject1,
            test_score=40,
            exam_score=60,
        )
        Result.objects.create(
            student=self.student2,
            session=self.session,
            term=self.term,
            current_class=self.student_class,
            subject=self.subject1,
            test_score=30,
            exam_score=50,
        )

        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("view-results"))

        results = response.context["results"]
        self.assertIn(self.student1.id, results)
        self.assertIn(self.student2.id, results)
        self.assertEqual(results[self.student1.id]["student"], self.student1)
        self.assertEqual(results[self.student2.id]["student"], self.student2)

    def test_result_list_view_includes_subjects(self):
        """Test that result list includes all subjects for each student"""
        Result.objects.create(
            student=self.student1,
            session=self.session,
            term=self.term,
            current_class=self.student_class,
            subject=self.subject1,
            test_score=40,
            exam_score=60,
        )
        Result.objects.create(
            student=self.student1,
            session=self.session,
            term=self.term,
            current_class=self.student_class,
            subject=self.subject2,
            test_score=35,
            exam_score=55,
        )

        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("view-results"))

        results = response.context["results"]
        student_subjects = results[self.student1.id]["subjects"]
        self.assertEqual(len(student_subjects), 2)


class ResultModelTestCase(TestCase):
    """Tests for result model methods"""

    def setUp(self):
        self.session = AcademicSession.objects.create(name="2024/2025", current=True)
        self.term = AcademicTerm.objects.create(name="First Term", current=True)
        self.student_class = StudentClass.objects.create(name="Grade 1 Model")
        self.subject = Subject.objects.create(name="Mathematics-Model")
        self.student = Student.objects.create(
            registration_number="001-model",
            firstname="John",
            surname="Doe",
            current_class=self.student_class,
        )

    def test_result_total_score_calculation(self):
        """Test that total_score method calculates correctly"""
        result = Result.objects.create(
            student=self.student,
            session=self.session,
            term=self.term,
            current_class=self.student_class,
            subject=self.subject,
            test_score=40,
            exam_score=60,
        )
        self.assertEqual(result.total_score(), 100)

    def test_result_str_representation(self):
        """Test result string representation"""
        result = Result.objects.create(
            student=self.student,
            session=self.session,
            term=self.term,
            current_class=self.student_class,
            subject=self.subject,
        )
        expected = f"{self.student} {self.session} {self.term} {self.subject}"
        self.assertEqual(str(result), expected)
