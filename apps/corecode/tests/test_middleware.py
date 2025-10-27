from django.test import RequestFactory, TestCase

from apps.corecode.middleware import SiteWideConfigs
from apps.corecode.models import AcademicSession, AcademicTerm


class MiddlewareTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.session = AcademicSession.objects.create(name="2024/2025", current=True)
        self.term = AcademicTerm.objects.create(name="First Term", current=True)

    def test_middleware_adds_session_and_term_to_request(self):
        """Test that middleware adds current_session and current_term to request"""

        def get_response(request):
            return None

        middleware = SiteWideConfigs(get_response)
        request = self.factory.get("/")
        middleware(request)

        self.assertEqual(request.current_session, self.session)
        self.assertEqual(request.current_term, self.term)

    def test_middleware_with_no_current_session_raises_error(self):
        """Test that middleware raises error when no current session exists"""
        AcademicSession.objects.all().update(current=False)

        def get_response(request):
            return None

        middleware = SiteWideConfigs(get_response)
        request = self.factory.get("/")

        with self.assertRaises(AcademicSession.DoesNotExist):
            middleware(request)

    def test_middleware_with_no_current_term_raises_error(self):
        """Test that middleware raises error when no current term exists"""
        AcademicTerm.objects.all().update(current=False)

        def get_response(request):
            return None

        middleware = SiteWideConfigs(get_response)
        request = self.factory.get("/")

        with self.assertRaises(AcademicTerm.DoesNotExist):
            middleware(request)

    def test_middleware_returns_response_from_get_response(self):
        """Test that middleware properly returns the response from get_response"""
        expected_response = "test_response"

        def get_response(request):
            return expected_response

        middleware = SiteWideConfigs(get_response)
        request = self.factory.get("/")
        response = middleware(request)

        self.assertEqual(response, expected_response)
