# Bob Go Shipping for ERPNext

BobGoShipping connects ERPNext's standard Shipment workflow to Bob Go. The app lets ERPNext users fetch Bob Go courier rates, create Bob Go shipments from selected services, print PDF shipping labels, and keep shipment tracking information synced on ERPNext Shipments and linked Delivery Notes.

Bob Go is the courier aggregation platform this app integrates with.

## Key features

- Fetch available Bob Go courier services from an ERPNext Shipment.
- Select a returned service and create the shipment in Bob Go.
- Store the Bob Go shipment ID, carrier, carrier service, shipment amount, AWB/tracking reference, tracking status, and tracking detail on the ERPNext Shipment.
- Print the Bob Go waybill/shipping label as a private PDF attachment on the Shipment.
- Update tracking manually from the Shipment, automatically through Bob Go webhooks, or through the daily scheduler.
- Copy or automatically subscribe the Bob Go webhook URLs for tracking updates and shipment submission status updates.
- Write shipping and tracking information back to linked Delivery Notes in read-only custom fields.
- Use Bob Go production or sandbox APIs from the same settings page.

## Screenshots

After **Fetch Shipping Rates**, choose a courier service in the selection dialog (preferred services appear when configured in Parcel Service Types).

<img src="media/Screenshot%202026-05-04%20at%2019.36.43.png" alt="ERPNext Shipment: Select Service to Create Shipment dialog showing Bob Go carrier and price" width="800" style="max-width: 100%; height: auto;" />

When Bob Go accepts the booking, ERPNext shows a confirmation with the Bob Go shipment number.

<img src="media/Screenshot%202026-05-04%20at%2019.45.29.png" alt="Shipment Created success message after booking with Bob Go" width="800" style="max-width: 100%; height: auto;" />

**Print Shipping Label** downloads the waybill from Bob Go and saves it as a PDF attachment on the Shipment.

<img src="media/Screenshot%202026-05-04%20at%2019.45.42.png" alt="Bob Go shipping label PDF with carrier branding and barcodes" width="800" style="max-width: 100%; height: auto;" />

The submitted Shipment stores Bob Go identifiers, carrier, service, amount, AWB, and tracking fields.

<img src="media/Screenshot%202026-05-04%20at%2019.45.49.png" alt="ERPNext Shipment form with Bob Go service provider, shipment ID, and tracking status" width="800" style="max-width: 100%; height: auto;" />

## Compatibility and requirements

- Frappe Framework: `>=15.0.0,<17.0.0`
- ERPNext: required
- Hosting: Frappe Cloud or self-hosted Frappe Bench
- Bob Go account with an API bearer token
- A publicly reachable HTTPS ERPNext site if Bob Go webhooks will be used

The app does not require extra Ubuntu/apt packages on Frappe Cloud.

## What the app adds to ERPNext

The app creates read-only custom fields on **Delivery Note** under a **Shipping Details** section:

- Delivery Type
- Parcel Service
- Parcel Service Type
- Tracking Number
- Tracking URL
- Tracking Status
- Tracking Status Information

It also adds Bob Go actions to the standard ERPNext **Shipment** form and schedules a daily tracking update job for booked Bob Go shipments that have not yet been delivered.

## Configure Bob Go

Only users with the **System Manager** role can configure Bob Go settings.

1. In ERPNext Desk, use the search bar to open **BobGo**.
2. Enable **Enabled?**.
3. Leave **Use Test Environment?** unchecked for production, or check it to use the Bob Go sandbox API.
4. Paste your Bob Go API token into **Bearer Token**.
5. Enter a strong shared secret in **Webhook Secret**. This is used to validate inbound Bob Go webhook calls.
6. Keep **Default Timeout ms** at `10000` unless Bob Go has advised a different timeout.
7. Save the settings.

The integration uses these Bob Go API base URLs:

- Production: `https://api.bobgo.co.za/v2`
- Sandbox: `https://api.sandbox.bobgo.co.za/v2`

## Configure webhooks

Webhooks are recommended because Bob Go shipment submission and tracking updates can be asynchronous.

After saving **Bearer Token** and **Webhook Secret**, use either the automatic or manual setup flow.

### Automatic setup

1. Open **BobGo** settings.
2. Click **Subscribe Webhooks**.
3. Click **Refresh Webhook Status**.
4. Confirm that these read-only checks are enabled:
   - **Tracking Webhook Subscribed?**
   - **Shipment Submission Status Webhook Subscribed?**

The button safely checks existing Bob Go webhook subscriptions and only creates missing active subscriptions.

### Manual setup

1. Open **BobGo** settings.
2. Click **Copy Tracking Update URL** and register it in Bob Go for the `tracking/updated` topic.
3. Click **Copy Shipment Submission Status Update URL** and register it in Bob Go for the `shipment_submission_status/updated` topic.
4. Click **Refresh Webhook Status** in ERPNext to confirm Bob Go reports both subscriptions as active.

Both webhook endpoints expect `POST` requests with `application/json`. The copied URLs include the configured secret. Do not share these URLs publicly. If a URL is exposed, change the **Webhook Secret**, save the settings, and resubscribe the webhooks.

## ERPNext data required before fetching rates

Before using Bob Go on a Shipment, make sure the following ERPNext records are complete:

- Bob Go is enabled and the bearer token is saved in **BobGo** settings.
- The Shipment is submitted and does not already have a Shipment ID.
- Pickup and delivery addresses have at least address line 1, city, country, and postal code/pincode.
- The ERPNext Country record has a country code.
- Pickup and delivery contacts have a first name, last name, email address, and phone or mobile number.
- The pickup phone number starts with `+` and contains digits, for example `+27111234567`.
- If pickup is from a Company, the selected pickup contact person is an ERPNext User with a phone number.
- Shipment parcels have length, width, and height of at least `1 cm`, plus weight and quantity/count.
- Value of goods is set on the Shipment.

## Use Bob Go in ERPNext

### 1. Create and submit a Shipment

Create a standard ERPNext **Shipment** with pickup details, delivery details, parcel rows, delivery notes if applicable, pickup date, and value of goods. Submit the Shipment.

The Bob Go rate button is shown only when the Shipment is submitted and has no existing external Shipment ID.

### 2. Fetch Bob Go shipping rates

On the submitted Shipment, click **Fetch Shipping Rates**. The app sends the pickup address, delivery address, parcel dimensions, contacts, and declared value to Bob Go and returns available services sorted by price.

If the Shipment contains more than one parcel row, ERPNext warns that estimated rates may differ from the final carrier charge when packages have varying weights.

### 3. Select a service and create the Bob Go shipment

Choose a service from the rate selection dialog. ERPNext sends the selected provider slug and service level code to Bob Go and stores the returned booking information on the Shipment.

If Bob Go reports immediate success, the ERPNext Shipment status is set to **Booked**. If Bob Go returns a pending submission status, the integration keeps the returned identifiers and status detail, then webhooks or tracking updates can complete the status later.

### 4. Print the shipping label

After the shipment has a Bob Go Shipment ID, open **Tools > Print Shipping Label** on the Shipment. The app fetches the Bob Go waybill by tracking reference and saves it as a private PDF file attached to the Shipment.

### 5. Update or view tracking

After the shipment has a Bob Go Shipment ID, the Shipment form provides these actions:

- **Tools > Update Tracking**: fetches the latest tracking information from Bob Go and updates the Shipment and linked Delivery Notes.
- **View > Track Status**: opens the tracking URL if Bob Go returned one.

Tracking also updates automatically when Bob Go sends webhook events, and once per day through the scheduler for booked Bob Go shipments that are not delivered.

## Delivery Note updates

When a Bob Go shipment is created for a Shipment linked to Delivery Notes, the app updates each linked Delivery Note with the selected parcel service information. When tracking data is received, it also updates the Delivery Note tracking fields.

These fields are read-only because the Shipment and Bob Go tracking data are the source of truth.

## Optional service catalogue setup

The integration can fetch and display Bob Go rates without pre-creating every carrier or service in ERPNext. The optional service catalogue is useful when you want cleaner service names, aliases, or preferred services.

### Parcel Service

Use **Parcel Service** to maintain courier or carrier records. The DocType stores:

- Parcel Service Name
- Parcel Service Code
- URL Reference

The URL reference can be used for local tracking URL templates where applicable. Bob Go tracking URLs are saved from Bob Go responses when Bob Go provides them.

### Parcel Service Type

Use **Parcel Service Type** to maintain service levels for a parcel service. You can add aliases in the **Parcel Service Type Alias** child table and enable **Show in Preferred Services List**.

When fetched Bob Go rates match a configured service type or alias, the rate selector can show those rates in the preferred services group.

## Bob Go API actions used by this app

The integration uses the configured bearer token with Bob Go API v2 for these actions:

- `POST /rates` to fetch available courier rates.
- `POST /shipments` to create a Bob Go shipment.
- `GET /shipments/waybill` to fetch the PDF shipping label by tracking reference.
- `GET /tracking` to poll shipment tracking by tracking reference.
- `GET /webhooks` to read existing webhook subscriptions.
- `POST /webhooks` to subscribe missing webhook topics.

## Security notes

- The Bob Go bearer token and webhook secret are stored in ERPNext password fields.
- Webhook endpoints allow guest access so Bob Go can call them, but each request must include the configured shared secret.
- Webhook requests must be JSON `POST` requests.
- Webhook payloads larger than 128 KB are rejected.
- Do not share webhook URLs because the generated URLs include the shared secret.

## Troubleshooting

### No rates are returned

Check that Bob Go is enabled, the bearer token is valid, the correct production or sandbox environment is selected, addresses have country and postal code, contacts have phone numbers, parcel dimensions are valid, and Bob Go supports the requested collection and delivery route.

### Pickup phone validation fails

The pickup phone must start with `+` and contain digits. For Company pickups, update the phone number on the selected ERPNext User. For non-Company pickups, update the linked Contact phone or mobile number.

### Contact validation fails

Delivery and pickup contacts should have a last name. If the phone field is empty, the app uses the mobile number where available.

### Webhook status does not become subscribed

Confirm the ERPNext site is publicly reachable over HTTPS, the bearer token can manage Bob Go webhooks, the webhook secret is saved, and the site URL copied from ERPNext is the public Frappe Cloud or production site URL.

### A webhook is received but no Shipment is updated

The app matches Bob Go webhooks to ERPNext Shipments by Bob Go tracking reference or Bob Go shipment ID. Check that the Shipment was created through this integration and that its **Service Provider** is `BobGo`.

### Label printing fails

Confirm the Shipment has a Bob Go AWB/tracking reference. The app expects Bob Go to return a valid PDF label. If Bob Go returns a non-PDF response, the details are written to the ERPNext Error Log.

## Support and maintenance

Cohenix Website: https://www.cohenix.com/

Maintainer: Cohenix Support <support@cohenix.com>

Repository: https://github.com/EPIUSECX/Bob-Go-Shipping

## License

MIT
