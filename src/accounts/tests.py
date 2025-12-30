from django.test import TestCase
from django.contrib.auth.models import User


class RegistrationTest(TestCase):
    def test_registration_success(self):
        payload = {
            "username": "testuser",
            "password": "testpassword123",
            "email": "test@example.com",
        }
        response = self.client.post(
            "/api/v1/users/register", data=payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "User registered successfully")
        self.assertEqual(data["data"]["username"], "testuser")
        self.assertTrue(User.objects.filter(username="testuser").exists())

    def test_registration_duplicate_username(self):
        User.objects.create_user(username="existinguser", password="password123")
        payload = {"username": "existinguser", "password": "newpassword123"}
        response = self.client.post(
            "/api/v1/users/register", data=payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "Username already exists")

    def test_registration_invalid_data(self):
        # Short username
        payload = {"username": "hi", "password": "testpassword123"}
        response = self.client.post(
            "/api/v1/users/register", data=payload, content_type="application/json"
        )
        self.assertEqual(
            response.status_code, 422
        )  # Unprocessable Entity (Ninja validation error)

    def test_me_unauthenticated(self):
        response = self.client.get("/api/v1/users/me")
        self.assertEqual(response.status_code, 401)

    def test_token_login_success(self):
        User.objects.create_user(username="testuser", password="testpassword123")
        payload = {"username": "testuser", "password": "testpassword123"}
        response = self.client.post(
            "/api/v1/users/login", data=payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)
