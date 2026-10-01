import unittest

from fastapi.routing import APIRoute

from backend.admin_auth import require_admin_key
from backend.main import app
from backend.routers.orders import router as orders_router
from backend.routers.products import router as products_router


class RouteSecurityTests(unittest.TestCase):
    def test_admin_routes_require_key_and_public_routes_do_not(self):
        # FastAPI 0.141 keeps included routers live, so inspect their own routes.
        routes = {
            (method, route.path): route
            for router in (orders_router, products_router)
            for route in router.routes
            if isinstance(route, APIRoute)
            for method in route.methods
        }
        protected = (
            ("POST", "/products"),
            ("PATCH", "/products/{product_id}"),
            ("GET", "/orders"),
            ("GET", "/orders/{order_id}"),
            ("PATCH", "/orders/{order_id}/status"),
        )
        public = (
            ("GET", "/products"),
            ("GET", "/products/{product_id}"),
            ("POST", "/orders"),
        )
        published_paths = app.openapi()["paths"]
        for key in protected:
            with self.subTest(key=key):
                self.assertIn(key[1], published_paths)
                self.assertIn(require_admin_key, [d.call for d in routes[key].dependant.dependencies])
        for key in public:
            with self.subTest(key=key):
                self.assertIn(key[1], published_paths)
                self.assertNotIn(require_admin_key, [d.call for d in routes[key].dependant.dependencies])


if __name__ == "__main__":
    unittest.main()
