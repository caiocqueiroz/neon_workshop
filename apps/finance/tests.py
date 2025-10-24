from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass
from apps.students.models import Student

from .models import Invoice, InvoiceItem, Receipt


class InvoiceSignalTestCase(TestCase):
    """Tests for invoice signal handlers"""

    def setUp(self):
        self.session = AcademicSession.objects.create(name="2024/2025", current=True)
        self.term1 = AcademicTerm.objects.create(name="First Term", current=True)
        self.term2 = AcademicTerm.objects.create(name="Second Term", current=False)
        self.student_class = StudentClass.objects.create(name="Grade 1")
        self.student = Student.objects.create(
            registration_number="001",
            firstname="John",
            surname="Doe",
            current_class=self.student_class,
        )

    def test_previous_invoice_closed_on_new_invoice_creation(self):
        """Test that creating a new invoice closes the previous one"""
        # Create first invoice
        invoice1 = Invoice.objects.create(
            student=self.student,
            session=self.session,
            term=self.term1,
            class_for=self.student_class,
        )
        self.assertEqual(invoice1.status, "active")

        # Create second invoice
        invoice2 = Invoice.objects.create(
            student=self.student,
            session=self.session,
            term=self.term2,
            class_for=self.student_class,
        )

        # Verify that invoice1 was closed
        invoice1.refresh_from_db()
        self.assertEqual(invoice1.status, "closed")
        self.assertEqual(invoice2.status, "active")

    def test_balance_transfer_from_previous_invoice(self):
        """Test that balance from previous invoice is transferred to new one"""
        # Create first invoice with items and partial payment
        invoice1 = Invoice.objects.create(
            student=self.student,
            session=self.session,
            term=self.term1,
            class_for=self.student_class,
        )
        InvoiceItem.objects.create(invoice=invoice1, description="Tuition", amount=1000)
        InvoiceItem.objects.create(invoice=invoice1, description="Books", amount=200)
        Receipt.objects.create(invoice=invoice1, amount_paid=500)

        # Balance should be 700 (1200 - 500)
        self.assertEqual(invoice1.balance(), 700)

        # Create second invoice
        invoice2 = Invoice.objects.create(
            student=self.student,
            session=self.session,
            term=self.term2,
            class_for=self.student_class,
        )

        # Verify balance was transferred
        invoice2.refresh_from_db()
        self.assertEqual(invoice2.balance_from_previous_term, 700)

    def test_first_invoice_has_no_previous_balance(self):
        """Test that first invoice has no balance from previous term"""
        invoice = Invoice.objects.create(
            student=self.student,
            session=self.session,
            term=self.term1,
            class_for=self.student_class,
        )

        self.assertEqual(invoice.balance_from_previous_term, 0)
        self.assertEqual(invoice.status, "active")

    def test_invoice_for_different_student_not_affected(self):
        """Test that invoices for different students don't affect each other"""
        student2 = Student.objects.create(
            registration_number="002",
            firstname="Jane",
            surname="Smith",
            current_class=self.student_class,
        )

        # Create invoices for two different students
        invoice1 = Invoice.objects.create(
            student=self.student,
            session=self.session,
            term=self.term1,
            class_for=self.student_class,
        )

        invoice2 = Invoice.objects.create(
            student=student2,
            session=self.session,
            term=self.term1,
            class_for=self.student_class,
        )

        # Both should be active
        self.assertEqual(invoice1.status, "active")
        self.assertEqual(invoice2.status, "active")


class InvoiceViewTestCase(TestCase):
    """Tests for invoice views"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.session = AcademicSession.objects.create(name="2024/2025", current=True)
        self.term = AcademicTerm.objects.create(name="First Term", current=True)
        self.student_class = StudentClass.objects.create(name="Grade 1")
        self.student = Student.objects.create(
            registration_number="001",
            firstname="John",
            surname="Doe",
            current_class=self.student_class,
        )

    def test_invoice_list_view_requires_login(self):
        """Test that invoice list view requires authentication"""
        response = self.client.get(reverse("invoice-list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_invoice_list_view_accessible_when_logged_in(self):
        """Test that invoice list view is accessible when logged in"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("invoice-list"))
        self.assertEqual(response.status_code, 200)

    def test_invoice_create_view_requires_login(self):
        """Test that invoice create view requires authentication"""
        response = self.client.get(reverse("invoice-create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_invoice_detail_view_requires_login(self):
        """Test that invoice detail view requires authentication"""
        invoice = Invoice.objects.create(
            student=self.student,
            session=self.session,
            term=self.term,
            class_for=self.student_class,
        )
        response = self.client.get(reverse("invoice-detail", kwargs={"pk": invoice.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_invoice_detail_view_shows_items_and_receipts(self):
        """Test that invoice detail view displays items and receipts"""
        self.client.login(username="testuser", password="testpass123")
        invoice = Invoice.objects.create(
            student=self.student,
            session=self.session,
            term=self.term,
            class_for=self.student_class,
        )
        InvoiceItem.objects.create(invoice=invoice, description="Tuition", amount=1000)
        Receipt.objects.create(invoice=invoice, amount_paid=500)

        response = self.client.get(reverse("invoice-detail", kwargs={"pk": invoice.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("receipts", response.context)
        self.assertIn("items", response.context)
        self.assertEqual(len(response.context["items"]), 1)
        self.assertEqual(len(response.context["receipts"]), 1)

    def test_receipt_create_requires_invoice_parameter(self):
        """Test that receipt creation requires invoice parameter"""
        self.client.login(username="testuser", password="testpass123")
        invoice = Invoice.objects.create(
            student=self.student,
            session=self.session,
            term=self.term,
            class_for=self.student_class,
        )
        response = self.client.get(reverse("receipt-create") + f"?invoice={invoice.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("invoice", response.context)
        self.assertEqual(response.context["invoice"], invoice)

    def test_bulk_invoice_view_requires_login(self):
        """Test that bulk invoice view requires authentication"""
        response = self.client.get(reverse("bulk-invoice"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_bulk_invoice_view_accessible_when_logged_in(self):
        """Test that bulk invoice view is accessible when logged in"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("bulk-invoice"))
        self.assertEqual(response.status_code, 200)


class InvoiceModelTestCase(TestCase):
    """Tests for invoice model methods"""

    def setUp(self):
        self.session = AcademicSession.objects.create(name="2024/2025", current=True)
        self.term = AcademicTerm.objects.create(name="First Term", current=True)
        self.student_class = StudentClass.objects.create(name="Grade 1")
        self.student = Student.objects.create(
            registration_number="001",
            firstname="John",
            surname="Doe",
            current_class=self.student_class,
        )

    def test_invoice_balance_calculation(self):
        """Test that invoice balance is calculated correctly"""
        invoice = Invoice.objects.create(
            student=self.student,
            session=self.session,
            term=self.term,
            class_for=self.student_class,
            balance_from_previous_term=100,
        )
        InvoiceItem.objects.create(invoice=invoice, description="Tuition", amount=1000)
        InvoiceItem.objects.create(invoice=invoice, description="Books", amount=200)
        Receipt.objects.create(invoice=invoice, amount_paid=500)

        # Total payable: 100 (previous) + 1200 (items) = 1300
        # Paid: 500
        # Balance: 800
        self.assertEqual(invoice.amount_payable(), 1200)
        self.assertEqual(invoice.total_amount_payable(), 1300)
        self.assertEqual(invoice.total_amount_paid(), 500)
        self.assertEqual(invoice.balance(), 800)

    def test_invoice_with_no_items_has_zero_amount_payable(self):
        """Test that invoice with no items has zero amount payable"""
        invoice = Invoice.objects.create(
            student=self.student,
            session=self.session,
            term=self.term,
            class_for=self.student_class,
        )
        self.assertEqual(invoice.amount_payable(), 0)
        self.assertEqual(invoice.total_amount_payable(), 0)

    def test_invoice_with_no_receipts_has_zero_amount_paid(self):
        """Test that invoice with no receipts has zero amount paid"""
        invoice = Invoice.objects.create(
            student=self.student,
            session=self.session,
            term=self.term,
            class_for=self.student_class,
        )
        self.assertEqual(invoice.total_amount_paid(), 0)
