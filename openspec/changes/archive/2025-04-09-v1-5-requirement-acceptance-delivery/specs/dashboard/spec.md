## MODIFIED Requirements

### Requirement: Dashboard summary data
The system SHALL return dashboard summary data including key metrics for the user's overview. The response SHALL include an `active_maintenance_count` field showing the count of active maintenance periods.

#### Scenario: Active maintenance count included
- **WHEN** the dashboard endpoint is called
- **THEN** the response includes `active_maintenance_count` as an integer count of maintenance periods with `status = active`
