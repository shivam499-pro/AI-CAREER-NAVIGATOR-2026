# Backend Response Contract

This document defines the response format for AI Career Navigator backend APIs.

## Unified Response Schema

All successful API responses should follow this structure:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "source": "db",
  "meta": {
    "timestamp": "2024-01-01T00:00:00Z",
    "execution_time_ms": 0
  }
}
```

## Response Field Meanings

### `success` (boolean)
- `true`: Request completed successfully
- `false`: Request failed but handled gracefully

### `data` (object|null)
- The actual payload
- Can be null for error cases

### `error` (string|null)
- `null` for successful requests
- Error message string for failures

### `source` (string)
Data source indicator:
- `"db"`: From database
- `"cache"`: From memory cache
- `"fallback"`: Using fallback data
- `"global_error_handler"`: Error caught by global handler

### `meta` (object)
- `timestamp`: ISO 8601 timestamp
- `execution_time_ms`: Request processing time

## API-Specific Contracts

### /api/interview/progress/{user_id}

Returns:
```json
{
  "sessions": [...],
  "rank": {"xp": 0, "level": 1, "rank_title": "..."},
  "streaks": {"current_streak": 0, "longest_streak": 0, "total_sessions": 0}
}
```

### /api/career/evolution/{user_id}

Returns:
```json
{
  "user_id": "uuid",
  "career_paths": [
    {
      "career_path": "AI/ML Engineer",
      "avg_score": 72,
      "trend": "improving",
      "volatility": 0.12,
      "total_sessions": 8,
      "confidence": 0.81
    }
  ],
  "overall_growth_state": "growing"
}
```

### /api/interview/generate-questions

Returns:
```json
{
  "success": true,
  "questions": [...],
  "source": "gemini|cache|fallback",
  "meta": {...}
}
```

## Fallback Rules

### Interview Questions
1. Try Gemini API
2. If fail → try cache
3. If fail → use fallback questions
4. Always return 200 OK with questions

### Memory Engine
- Non-critical feature
- Failures logged but don't break API
- Returns safe default if fails

### Evolution Engine  
- Cached for 15 minutes
- Returns fallback if no data
- Never breaks on errors

## Error Handling Rules

1. Never throw raw HTTPException(500) for external API failures
2. Always return fallback data when possible
3. Log errors server-side only
4. Never leak stack traces to frontend

## Global Error Handler

All unhandled exceptions are caught by global middleware and return:

```json
{
  "success": false,
  "data": null,
  "error": "Internal server error",
  "source": "global_error_handler",
  "meta": {
    "timestamp": "...",
    "execution_time_ms": 0
  }
}
```

## Health Check

GET /health returns:

```json
{
  "status": "healthy",
  "services": {
    "database": true,
    "gemini": true,
    "memory_engine": true
  }
}
```

Returns 200 OK regardless of service status.