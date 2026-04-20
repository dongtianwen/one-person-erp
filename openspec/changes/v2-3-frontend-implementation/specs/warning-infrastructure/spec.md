## ADDED Requirements

### Requirement: Warning code constant mapping
The system SHALL provide a `warnings.js` constant file mapping all warning_code strings to Chinese user-facing messages.

#### Scenario: Known warning code displays mapped message
- **WHEN** API response contains `warning_code: "SNAPSHOT_WRITE_FAILED"`
- **THEN** system displays "版本留痕写入失败，数据已保存，可稍后在历史记录中手动重建。"

#### Scenario: Unknown warning code displays fallback message
- **WHEN** API response contains `warning_code` not defined in WARNING_MESSAGES
- **THEN** system displays "操作完成，但存在异常，请查看日志"

### Requirement: useApiWarning composable
The system SHALL provide a `useApiWarning` composable that any component can import and use to handle warning_code in API responses.

#### Scenario: API response with warning_code triggers toast
- **WHEN** component calls `handleResponse(apiCall())` and response contains `warning_code`
- **THEN** system calls `ElMessage.warning` with the mapped Chinese message
- **THEN** composable returns the original response data without blocking

#### Scenario: API response without warning_code passes through
- **WHEN** component calls `handleResponse(apiCall())` and response does not contain `warning_code`
- **THEN** composable returns the original response data without showing any toast
