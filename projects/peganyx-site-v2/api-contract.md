# API Contract

## Endpoint(s)
- `GET /api/health` - deployment liveness/readiness probe
- `GET /api/site` - content contract for homepage and core marketing pages
- `POST /api/contact` - validated contact/get-started submission

## Request shape

### POST /api/contact
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "company": "Peganyx Prospect",
  "projectType": "Website redesign",
  "budget": "$5k-$15k",
  "timeline": "2-4 weeks",
  "message": "We want a sharper conversion-focused company site."
}
```

Required fields: `name`, `email`, `message`.

## Response shape

### GET /api/site
```json
{
  "meta": {
    "generatedAt": "ISO-8601",
    "environment": "production",
    "version": "0.1.0"
  },
  "company": {
    "name": "Peganyx",
    "tagline": "string"
  },
  "navigation": [{ "label": "Services", "href": "/services" }],
  "home": { "hero": {}, "proof": [], "services": [], "process": [], "faq": [] },
  "pages": {
    "services": {},
    "about": {},
    "contact": {}
  }
}
```

### POST /api/contact
```json
{
  "data": {
    "accepted": true,
    "submissionId": "cnt_xxx",
    "receivedAt": "ISO-8601"
  },
  "meta": {
    "generatedAt": "ISO-8601",
    "environment": "production",
    "version": "0.1.0"
  }
}
```

## Error behavior
All errors return JSON:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required",
    "details": {}
  },
  "meta": {
    "generatedAt": "ISO-8601",
    "environment": "production",
    "version": "0.1.0"
  }
}
```

Typical status codes:
- `400` invalid request body / missing required fields
- `405` unsupported method (when applicable)
- `500` unexpected server error

## Notes
- The contact endpoint is stateless and Vercel-safe; it validates and acknowledges submissions but does not yet persist to a CRM/database.
- The site content contract is intentionally broad enough to support the redesigned marketing pages without hard-coupling FE to presentational markup.
