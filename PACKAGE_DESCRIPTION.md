# Bob Go Shipping for ERPNext

BobGoShipping connects ERPNext's standard Shipment workflow to Bob Go. The app lets ERPNext users fetch Bob Go courier rates, create Bob Go shipments from selected services, print PDF shipping labels, and keep shipment tracking information synced on ERPNext Shipments and linked Delivery Notes.

## Key features

- Fetch available Bob Go courier services from an ERPNext Shipment.
- Select a returned service and create the shipment in Bob Go.
- Store Bob Go shipment identifiers, carrier details, shipment amount, AWB/tracking reference, tracking status, and tracking detail on the ERPNext Shipment.
- Print the Bob Go waybill/shipping label as a private PDF attachment on the Shipment.
- Update tracking manually from the Shipment, through Bob Go webhooks, or through the daily scheduler.
- Write shipping and tracking information back to linked Delivery Notes in read-only custom fields.
- Use Bob Go production or sandbox APIs from the same settings page.

## Compatibility and requirements

- Frappe Framework: `>=15.0.0,<17.0.0`
- ERPNext: required
- Bob Go account with an API bearer token
- A publicly reachable HTTPS ERPNext site if Bob Go webhooks will be used

## Configuration overview

Only users with the **System Manager** role can configure Bob Go settings. The app stores the Bob Go bearer token and webhook secret in ERPNext password fields. Webhook endpoints allow guest access so Bob Go can call them, but each request must include the configured shared secret.

The integration supports rate lookup, shipment creation, label retrieval, tracking updates, webhook subscription management, and Delivery Note tracking updates.
