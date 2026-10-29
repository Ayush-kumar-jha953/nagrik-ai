import json
import unittest
import database
from app import app


class NagrikAITestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        database.init_db()
        # the site now needs a login: sign in (registers the test user on first run)
        res = self.client.post("/api/login", json={"username": "test_user@a", "name": "Test User", "password": "test1234"})
        self.assertEqual(res.status_code, 200)

    def test_00_login_gate(self):
        anon = app.test_client()
        res = anon.get("/")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers["Location"])
        self.assertEqual(anon.get("/api/posts").status_code, 401)
        self.assertEqual(anon.get("/login").status_code, 200)
        bad = anon.post("/api/login", json={"username": "test_user@a", "password": "wrong"})
        self.assertEqual(bad.status_code, 401)

    def test_01_index_page(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"NAGRIK AI", res.data)
        self.assertIn(b"Issues by category", res.data)
        self.assertIn(b"botFloatingBtn", res.data)

    def test_02_session_and_categories(self):
        res = self.client.get("/api/session")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["authenticated"])

        res_cat = self.client.get("/api/categories")
        self.assertEqual(res_cat.status_code, 200)
        cats = res_cat.get_json()
        self.assertIn("Infrastructure", cats)
        self.assertIn("Sanitation", cats)
        self.assertIn("Healthcare", cats)
        self.assertIn("Education", cats)
        self.assertIn("Climate Issue", cats)
        self.assertGreaterEqual(cats["Infrastructure"], 200)

    def test_03_get_posts(self):
        res = self.client.get("/api/posts?limit=20")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(len(data["posts"]) >= 10)
        self.assertGreaterEqual(data["total"], 1000)

    def test_04_create_post_valid_passes_ml(self):
        payload = {
            "category": "Infrastructure",
            "title": "Severe pothole cluster in Rohini Sector 22",
            "location": "Rohini Sector 22, North West Delhi",
            "description": "In my area Rohini sector-22, Near Mayur hostel there is very old abandon building which can collapse any time and also affect nearby buildings, I request authority to solve my problem.",
            "image_url": "/static/assets/post_abandoned_building.png"
        }
        res = self.client.post("/api/posts", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertFalse(data["flagged"])
        self.assertIn("post", data)
        self.assertTrue("ai_solution" in data["post"])

    def test_05_create_post_flagged_by_ml_fails(self):
        payload = {
            "category": "Sanitation",
            "description": "kutta saala chor corrupt minister madarchod",
            "image_url": "/static/assets/post_garbage.png"
        }
        res = self.client.post("/api/posts", json=payload)
        self.assertEqual(res.status_code, 422)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertTrue(data["flagged"])

    def test_06_like_and_comment(self):
        posts_res = self.client.get("/api/posts?limit=1").get_json()["posts"]
        post_id = posts_res[0]["id"]

        like_res = self.client.post(f"/api/posts/{post_id}/like").get_json()
        self.assertTrue(like_res["success"])

        comment_res = self.client.post(f"/api/posts/{post_id}/comment", json={"comment": "Support this civic report!"})
        self.assertEqual(comment_res.status_code, 200)
        cdata = comment_res.get_json()
        self.assertTrue(cdata["success"])

    def test_07_statistics_and_zones(self):
        res = self.client.get("/api/statistics")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreaterEqual(data["total_complaints"], 1000)
        self.assertIn("red", data["zone_counts"])
        self.assertIn("yellow", data["zone_counts"])
        self.assertIn("green", data["zone_counts"])

    def test_08_delhi_map_locations(self):
        res = self.client.get("/api/map-locations")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreaterEqual(len(data["locations"]), 10)


if __name__ == "__main__":
    unittest.main()
