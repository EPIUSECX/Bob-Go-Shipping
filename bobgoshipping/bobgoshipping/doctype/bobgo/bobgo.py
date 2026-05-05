# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_url
from urllib.parse import quote

from .client import (
	BobGoUtils,
	get_bobgo_utils,
	get_expected_webhook_subscriptions,
	normalize_webhook_subscriptions,
)
from .constants import (
	BOBGO_PROVIDER,
	SUBMISSION_STATUS_WEBHOOK_TOPIC,
	TRACKING_WEBHOOK_TOPIC,
)
from .webhooks import handle_submission_status_webhook, handle_tracking_webhook


class BobGo(Document):
	def validate(self):
		if self.enabled and not self.get_password("bearer_token"):
			frappe.throw(_("Bearer Token is required when Bob Go is enabled."))
		if self.enabled and self.get("webhook_secret") and not self.get_password("webhook_secret"):
			frappe.throw(_("Webhook Secret could not be read. Please re-enter it."), title=_("Bob Go"))


@frappe.whitelist()
def copy_tracking_update_url():
	frappe.only_for("System Manager")
	return get_bobgo_webhook_url("tracking")


@frappe.whitelist()
def copy_shipment_submission_status_update_url():
	frappe.only_for("System Manager")
	return get_bobgo_webhook_url("submission")


@frappe.whitelist()
def subscribe_webhooks():
	frappe.only_for("System Manager")

	tracking_url, submission_url, bobgo, bobgo_utils = get_webhook_sync_context()

	expected_subscriptions = get_expected_webhook_subscriptions(tracking_url, submission_url)
	existing_subscriptions = get_existing_webhook_subscriptions(bobgo_utils)
	missing_subscriptions = [
		subscription
		for subscription in expected_subscriptions
		if not has_matching_active_subscription(existing_subscriptions, subscription)
	]

	if missing_subscriptions:
		# Subscribe only the missing/inactive webhook topics so the button can be
		# re-run safely without creating noisy duplicates every time.
		bobgo_utils.request("POST", "webhooks", json={"webhook_subscriptions": missing_subscriptions})
		existing_subscriptions = get_existing_webhook_subscriptions(bobgo_utils)

	return save_webhook_subscription_statuses(bobgo, existing_subscriptions, tracking_url, submission_url)


@frappe.whitelist()
def refresh_webhook_status():
	frappe.only_for("System Manager")

	tracking_url, submission_url, bobgo, bobgo_utils = get_webhook_sync_context()
	existing_subscriptions = get_existing_webhook_subscriptions(bobgo_utils)
	return save_webhook_subscription_statuses(bobgo, existing_subscriptions, tracking_url, submission_url)


@frappe.whitelist()
def sync_parcel_templates():
	frappe.only_for("System Manager")

	bobgo_utils = get_bobgo_utils()
	packages = bobgo_utils.get_packages()
	result = {"created": 0, "updated": 0, "skipped": 0, "total": len(packages)}
	used_template_names = set()

	for idx, package in enumerate(packages, start=1):
		template = get_parcel_template_from_package(package, idx, used_template_names)
		if not template:
			result["skipped"] += 1
			continue

		existing_name = frappe.db.exists(
			"Shipment Parcel Template", {"parcel_template_name": template["parcel_template_name"]}
		)
		if existing_name:
			doc = frappe.get_doc("Shipment Parcel Template", existing_name)
			doc.update(template)
			doc.save()
			result["updated"] += 1
		else:
			doc = frappe.new_doc("Shipment Parcel Template")
			doc.update(template)
			doc.insert()
			result["created"] += 1

	frappe.db.commit()
	return result


def get_parcel_template_from_package(
	package: dict, idx: int, used_template_names: set[str]
) -> dict | None:
	name = (package.get("name") or "").strip()
	length = flt(package.get("length_cm") or package.get("length"))
	width = flt(package.get("width_cm") or package.get("width"))
	height = flt(package.get("height_cm") or package.get("height"))

	if not name or length <= 0 or width <= 0 or height <= 0:
		return None

	weight = flt(
		package.get("weight_kg")
		or package.get("weight")
		or package.get("volumetric_weight")
		or package.get("volumetric_weight_kg")
	)
	if weight <= 0:
		weight = get_bobgo_volumetric_weight(length, width, height)

	return {
		"parcel_template_name": get_unique_parcel_template_name(name, package, idx, used_template_names),
		"length": length,
		"width": width,
		"height": height,
		"weight": weight,
	}


def get_unique_parcel_template_name(
	name: str, package: dict, idx: int, used_template_names: set[str]
) -> str:
	if name not in used_template_names:
		used_template_names.add(name)
		return name

	package_id = package.get("id")
	if package_id:
		candidate = _("{0} (Bob Go {1})").format(name, package_id)
	else:
		candidate = _("{0} (Bob Go {1})").format(name, idx)

	while candidate in used_template_names:
		candidate = f"{candidate[:130]} {frappe.generate_hash(length=8)}"

	used_template_names.add(candidate)
	return candidate


def get_bobgo_volumetric_weight(length: float, width: float, height: float) -> float:
	return flt((length * width * height) / 4000, 3)


def get_bobgo_webhook_url(webhook_type: str) -> str:
	webhook_secret = get_bobgo_webhook_secret()
	if not webhook_secret:
		frappe.throw(_("Please set the Bob Go Webhook Secret first."), title=_("Bob Go"))

	base_url = get_bobgo_public_base_url()
	secret = quote(webhook_secret, safe="")

	if webhook_type == "tracking":
		return (
			f"{base_url}/api/method/"
			"bobgoshipping.bobgoshipping.doctype.bobgo.bobgo.handle_tracking_webhook"
			f"?secret={secret}"
		)

	if webhook_type == "submission":
		return (
			f"{base_url}/api/method/"
			"bobgoshipping.bobgoshipping.doctype.bobgo.bobgo.handle_submission_status_webhook"
			f"?secret={secret}"
		)

	frappe.throw(_("Unknown Bob Go webhook type: {0}").format(webhook_type), title=_("Bob Go"))


def get_bobgo_public_base_url() -> str:
	if getattr(frappe.local, "request", None):
		proto = (
			frappe.get_request_header("X-Forwarded-Proto")
			or frappe.get_request_header("X-Forwarded-Protocol")
			or frappe.request.scheme
			or "https"
		)
		host = (
			frappe.get_request_header("X-Forwarded-Host")
			or frappe.get_request_header("Host")
			or frappe.request.host
		)
		if host:
			return f"{proto.split(',')[0].strip()}://{host.split(',')[0].strip()}".rstrip("/")

	return get_url().rstrip("/")


def get_bobgo_webhook_secret() -> str | None:
	settings = frappe.get_single("BobGo")
	try:
		return settings.get_password("webhook_secret")
	except frappe.ValidationError:
		frappe.throw(
			_("Please re-enter the Bob Go Webhook Secret and save the settings."),
			title=_("Bob Go"),
		)


def get_webhook_subscription_statuses(
	subscriptions: list[dict], tracking_url: str, submission_url: str
) -> dict[str, int]:
	return {
		"tracking_webhook_subscribed": int(
			has_matching_active_subscription(
				subscriptions,
				{"topic": TRACKING_WEBHOOK_TOPIC, "delivery_url": tracking_url, "status": "active"},
			)
		),
		"shipment_submission_status_webhook_subscribed": int(
			has_matching_active_subscription(
				subscriptions,
				{
					"topic": SUBMISSION_STATUS_WEBHOOK_TOPIC,
					"delivery_url": submission_url,
					"status": "active",
				},
			)
		),
	}


def has_matching_active_subscription(subscriptions: list[dict], expected_subscription: dict) -> bool:
	expected_url = (expected_subscription.get("delivery_url") or "").strip()
	expected_topic = (expected_subscription.get("topic") or "").strip()
	expected_status = (expected_subscription.get("status") or "active").strip().lower()

	for subscription in subscriptions:
		if (subscription.get("topic") or "").strip() != expected_topic:
			continue
		if (subscription.get("delivery_url") or "").strip() != expected_url:
			continue
		if (subscription.get("status") or "").strip().lower() != expected_status:
			continue
		return True

	return False


def get_webhook_sync_context():
	tracking_url = get_bobgo_webhook_url("tracking")
	submission_url = get_bobgo_webhook_url("submission")
	return tracking_url, submission_url, frappe.get_single("BobGo"), get_bobgo_utils()


def get_existing_webhook_subscriptions(bobgo_utils: BobGoUtils) -> list[dict]:
	return normalize_webhook_subscriptions(bobgo_utils.request("GET", "webhooks"))


def save_webhook_subscription_statuses(
	bobgo: Document, subscriptions: list[dict], tracking_url: str, submission_url: str
):
	statuses = get_webhook_subscription_statuses(subscriptions, tracking_url, submission_url)
	bobgo.db_set(statuses)
	return statuses
