import unittest

from fastapi import HTTPException
from pydantic import ValidationError

from app.profiles.schemas import SellerProfileUpdate
from app.moderation.schemas import ReportDecision
from app.safety.schemas import ReportCreate
from app.vehicles.filters import validate_filters
from app.vehicles.fields import public_listing_fields
from app.vehicles.lifecycle import resolve_listing_status
from app.vehicles.schemas import VehicleCreate


class VehicleRulesTests(unittest.TestCase):
    def test_vehicle_requires_valid_swiss_location_format(self):
        with self.assertRaises(ValidationError):
            VehicleCreate(
                title="Auto", brand="Marke", price=1000,
                postal_code="0123", locality="Zürich", canton="ZH",
            )

    def test_power_filter_is_rejected_for_bicycles(self):
        with self.assertRaises(HTTPException) as context:
            validate_filters("bicycles", {"power_min": 10})
        self.assertEqual(context.exception.status_code, 422)

    def test_listing_status_transitions_are_explicit(self):
        self.assertEqual(resolve_listing_status("active", "archive"), "archived")
        self.assertEqual(resolve_listing_status("archived", "reactivate"), "active")
        with self.assertRaises(HTTPException):
            resolve_listing_status("draft", "mark_sold")

    def test_bicycles_do_not_query_power_column(self):
        self.assertNotIn("power", public_listing_fields("bicycles").split(", "))


class ProfileAndSafetyRulesTests(unittest.TestCase):
    def test_dealer_requires_business_identity(self):
        with self.assertRaises(ValidationError):
            SellerProfileUpdate(seller_type="dealer")

    def test_private_seller_needs_no_business_identity(self):
        profile = SellerProfileUpdate(seller_type="private")
        self.assertEqual(profile.seller_type, "private")

    def test_report_subject_must_match_type(self):
        with self.assertRaises(ValidationError):
            ReportCreate(subject_type="message", reason="spam")

    def test_rejected_report_cannot_suspend_content(self):
        with self.assertRaises(ValidationError):
            ReportDecision(outcome="rejected", action="suspend_user", decision="Nicht bestätigt")


if __name__ == "__main__":
    unittest.main()
