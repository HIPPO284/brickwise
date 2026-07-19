# Catalog schema

The versioned schema is `ml/brickwise_ml/catalog/schema/part_catalog.schema.json`. Every record has explicit source, LDraw license/validation, unknown geometry/features, recognition state, and provenance. Design IDs are strings. Unknown values are null or explicit states such as `unknown`, `missing`, or `review_required`. Extra fields are rejected by the typed Pydantic models and JSON Schema.
