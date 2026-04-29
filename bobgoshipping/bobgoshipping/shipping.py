# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt
import json

import frappe
from erpnext.stock.doctype.shipment.shipment import get_company_contact

from bobgoshipping.bobgoshipping.doctype.bobgo.bobgo import BOBGO_PROVIDER, get_bobgo_utils
from bobgoshipping.bobgoshipping.utils import (
	get_address,
	get_contact,
	match_parcel_service_type_carrier,
)


@frappe.whitelist()
def fetch_shipping_rates(
	pickup_from_type,
	delivery_to_type,
	pickup_address_name,
	delivery_address_name,
	parcels,
	description_of_content,
	pickup_date,
	value_of_goods,
	pickup_contact_name=None,
	delivery_contact_name=None,
):
	# Return Shipping Rates for Bob Go.
	shipment_prices = []
	bobgo_enabled = frappe.db.get_single_value("BobGo", "enabled")
	pickup_address = get_address(pickup_address_name)
	delivery_address = get_address(delivery_address_name)
	parcels = json.loads(parcels)

	if bobgo_enabled:
		if pickup_from_type != "Company":
			pickup_contact = get_contact(pickup_contact_name)
		else:
			pickup_contact = get_company_contact(user=pickup_contact_name)
			pickup_contact.email_id = pickup_contact.pop("email", None)

		delivery_contact = get_contact(delivery_contact_name)

		bobgo = get_bobgo_utils()
		bobgo_prices = (
			bobgo.get_available_services(
				pickup_address=pickup_address,
				delivery_address=delivery_address,
				parcels=parcels,
				pickup_contact=pickup_contact,
				delivery_contact=delivery_contact,
				value_of_goods=value_of_goods,
			)
			or []
		)
		bobgo_prices = match_parcel_service_type_carrier(bobgo_prices, "carrier", "service_name")
		shipment_prices += bobgo_prices

	shipment_prices = [item for item in shipment_prices if "total_price" in item]
	shipment_prices = sorted(shipment_prices, key=lambda k: k["total_price"])
	return shipment_prices


@frappe.whitelist()
def create_shipment(
	shipment,
	pickup_from_type,
	delivery_to_type,
	pickup_address_name,
	delivery_address_name,
	shipment_parcel,
	description_of_content,
	pickup_date,
	value_of_goods,
	service_data,
	shipment_notific_email=None,
	tracking_notific_email=None,
	pickup_contact_name=None,
	delivery_contact_name=None,
	delivery_notes=None,
):
	if isinstance(delivery_notes, str):
		delivery_notes = json.loads(delivery_notes)

	if delivery_notes is None:
		delivery_notes = []

	service_info = json.loads(service_data)
	shipment_info, pickup_contact, delivery_contact = None, None, None
	pickup_address = get_address(pickup_address_name)
	delivery_address = get_address(delivery_address_name)

	if pickup_from_type != "Company":
		pickup_contact = get_contact(pickup_contact_name)

	else:
		pickup_contact = get_company_contact(user=pickup_contact_name)
		pickup_contact.email_id = pickup_contact.pop("email", None)

	delivery_contact = get_contact(delivery_contact_name)

	if service_info["service_provider"] == BOBGO_PROVIDER:
		bobgo = get_bobgo_utils()
		shipment_info = bobgo.create_shipment(
			shipment=shipment,
			pickup_address=pickup_address,
			delivery_address=delivery_address,
			shipment_parcel=shipment_parcel,
			value_of_goods=value_of_goods,
			pickup_contact=pickup_contact,
			delivery_contact=delivery_contact,
			service_info=service_info,
			pickup_date=pickup_date,
		)

	if shipment_info:
		shipment = frappe.get_doc("Shipment", shipment)
		update_values = {
			"service_provider": shipment_info.get("service_provider"),
			"carrier": shipment_info.get("carrier"),
			"carrier_service": shipment_info.get("carrier_service"),
			"shipment_id": shipment_info.get("shipment_id"),
			"shipment_amount": shipment_info.get("shipment_amount"),
			"awb_number": shipment_info.get("awb_number"),
			"tracking_url": shipment_info.get("tracking_url"),
		}

		# Bob Go submission can be asynchronous. We only mark the shipment as booked once
		# the provider reports a successful submission, otherwise we keep the external
		# identifiers and status detail without pretending the booking is finalized.
		if shipment_info.get("tracking_status"):
			update_values["tracking_status"] = shipment_info.get("tracking_status")
		if shipment_info.get("tracking_status_info"):
			update_values["tracking_status_info"] = shipment_info.get("tracking_status_info")
		if shipment_info.get("submission_status") in (None, "success"):
			update_values["status"] = "Booked"

		shipment.db_set(update_values)

		if delivery_notes:
			update_delivery_note(delivery_notes=delivery_notes, shipment_info=shipment_info)

	return shipment_info


@frappe.whitelist()
def print_shipping_label(shipment: str):
	shipment_doc = frappe.get_doc("Shipment", shipment)
	service_provider = shipment_doc.service_provider

	if service_provider == BOBGO_PROVIDER:
		bobgo = get_bobgo_utils()
		# Bob Go generates the label from the tracking reference / AWB number.
		content = bobgo.get_label(shipment_doc.awb_number)
		shipping_label = save_label_as_attachment(shipment, content)
	else:
		frappe.throw(frappe._("Shipment was not created with Bob Go."))

	return shipping_label


def save_label_as_attachment(shipment: str, content: bytes, index: int = None) -> str:
	"""Store label as attachment to Shipment and return the URL."""
	attachment = frappe.new_doc("File")
	if index is not None:
		attachment.file_name = f"label_{shipment}_{index}.pdf"
	else:
		attachment.file_name = f"label_{shipment}.pdf"
	attachment.content = content
	attachment.folder = "Home/Attachments"
	attachment.attached_to_doctype = "Shipment"
	attachment.attached_to_name = shipment
	attachment.is_private = 1
	attachment.save()
	return attachment.file_url


@frappe.whitelist()
def update_tracking(shipment, service_provider, shipment_id, delivery_notes=None):
	if isinstance(delivery_notes, str):
		delivery_notes = json.loads(delivery_notes)

	if delivery_notes is None:
		delivery_notes = []

	tracking_data = None
	if service_provider == BOBGO_PROVIDER:
		bobgo = get_bobgo_utils()
		shipment_doc = frappe.get_doc("Shipment", shipment)
		# Bob Go tracking lookups are keyed by tracking reference rather than shipment ID.
		tracking_data = bobgo.get_tracking_data(shipment_doc.awb_number)
	else:
		frappe.throw(frappe._("Shipment was not created with Bob Go."))

	if not tracking_data:
		return

	shipment = frappe.get_doc("Shipment", shipment)
	shipment.db_set(
		{
			"awb_number": tracking_data.get("awb_number"),
			"tracking_status": tracking_data.get("tracking_status"),
			"tracking_status_info": tracking_data.get("tracking_status_info"),
			"tracking_url": tracking_data.get("tracking_url"),
		}
	)

	if delivery_notes:
		update_delivery_note(delivery_notes=delivery_notes, tracking_info=tracking_data)

	return tracking_data


def update_delivery_note(delivery_notes, shipment_info=None, tracking_info=None):
	# Update Shipment Info in Delivery Note
	# Using db_set since some services might not exist
	delivery_notes = list(set(delivery_notes))

	for delivery_note in delivery_notes:
		dl_doc = frappe.get_doc("Delivery Note", delivery_note)
		if shipment_info:
			dl_doc.db_set("delivery_type", "Parcel Service")
			dl_doc.db_set("parcel_service", shipment_info.get("carrier"))
			dl_doc.db_set("parcel_service_type", shipment_info.get("carrier_service"))
		if tracking_info:
			dl_doc.db_set("tracking_number", tracking_info.get("awb_number"))
			dl_doc.db_set("tracking_url", tracking_info.get("tracking_url"))
			dl_doc.db_set("tracking_status", tracking_info.get("tracking_status"))
			dl_doc.db_set("tracking_status_info", tracking_info.get("tracking_status_info"))
