"""
Tests for services/jobs_service.py

Coverage targets (20 missing lines → 100%):
- search_jobs(): missing API key (ValueError), success with results,
  success with empty results, missing fields in job data, location
  param included/excluded, HTTP error raised
- get_linkedin_jobs_url(): with location, without location, spaces in keywords
- get_internship_url(): spaces replaced with hyphens
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx


# ===========================================================================
# search_jobs()
# ===========================================================================


class TestSearchJobs:
    @patch.dict("os.environ", {}, clear=True)
    async def test_raises_value_error_when_api_key_missing(self):
        """SERPAPI_KEY not set → ValueError raised before any HTTP call."""
        from services.jobs_service import search_jobs

        with pytest.raises(ValueError, match="SERPAPI_KEY is not configured"):
            await search_jobs("backend engineer")

    @patch.dict("os.environ", {"SERPAPI_KEY": "test-api-key"})
    @patch("services.jobs_service.httpx.AsyncClient")
    async def test_returns_parsed_job_list_on_success(self, mock_async_client):
        """Successful API call → jobs parsed into normalized dict format."""
        from services.jobs_service import search_jobs

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "jobs_results": [
                {
                    "job_id": "job-1",
                    "title": "Backend Engineer",
                    "company_name": "TechCo",
                    "location": "Remote",
                    "job_type": "Full-time",
                    "related_links": [{"link": "https://example.com/job-1"}],
                    "description": "Build APIs",
                }
            ]
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await search_jobs("backend engineer")

        assert len(result) == 1
        assert result[0]["id"] == "job-1"
        assert result[0]["title"] == "Backend Engineer"
        assert result[0]["company"] == "TechCo"
        assert result[0]["location"] == "Remote"
        assert result[0]["type"] == "Full-time"
        assert result[0]["url"] == "https://example.com/job-1"
        assert result[0]["description"] == "Build APIs"

    @patch.dict("os.environ", {"SERPAPI_KEY": "test-api-key"})
    @patch("services.jobs_service.httpx.AsyncClient")
    async def test_returns_empty_list_when_no_jobs_found(self, mock_async_client):
        """API returns no jobs_results key → empty list returned."""
        from services.jobs_service import search_jobs

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {}

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await search_jobs("nonexistent role")

        assert result == []

    @patch.dict("os.environ", {"SERPAPI_KEY": "test-api-key"})
    @patch("services.jobs_service.httpx.AsyncClient")
    async def test_limits_results_to_10_jobs(self, mock_async_client):
        """API returns more than 10 jobs → only first 10 are processed."""
        from services.jobs_service import search_jobs

        jobs = [
            {
                "job_id": f"job-{i}",
                "title": f"Engineer {i}",
                "company_name": "Co",
                "location": "Remote",
                "job_type": "Full-time",
                "related_links": [{"link": f"https://example.com/{i}"}],
                "description": "desc",
            }
            for i in range(15)
        ]
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"jobs_results": jobs}

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await search_jobs("engineer")

        assert len(result) == 10

    @patch.dict("os.environ", {"SERPAPI_KEY": "test-api-key"})
    @patch("services.jobs_service.httpx.AsyncClient")
    async def test_handles_missing_fields_with_defaults(self, mock_async_client):
        """Job entries missing fields → defaults to empty string, not KeyError."""
        from services.jobs_service import search_jobs

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "jobs_results": [{}]  # completely empty job entry
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await search_jobs("engineer")

        assert len(result) == 1
        assert result[0]["id"] == ""
        assert result[0]["title"] == ""
        assert result[0]["url"] == ""

    @patch.dict("os.environ", {"SERPAPI_KEY": "test-api-key"})
    @patch("services.jobs_service.httpx.AsyncClient")
    async def test_includes_location_param_when_provided(self, mock_async_client):
        """location argument → 'location' added to query params."""
        from services.jobs_service import search_jobs

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"jobs_results": []}

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        await search_jobs("engineer", location="San Francisco")

        call_kwargs = mock_client_instance.get.call_args[1]
        assert call_kwargs["params"]["location"] == "San Francisco"

    @patch.dict("os.environ", {"SERPAPI_KEY": "test-api-key"})
    @patch("services.jobs_service.httpx.AsyncClient")
    async def test_excludes_location_param_when_not_provided(self, mock_async_client):
        """No location argument → 'location' key absent from params."""
        from services.jobs_service import search_jobs

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"jobs_results": []}

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        await search_jobs("engineer")

        call_kwargs = mock_client_instance.get.call_args[1]
        assert "location" not in call_kwargs["params"]

    @patch.dict("os.environ", {"SERPAPI_KEY": "test-api-key"})
    @patch("services.jobs_service.httpx.AsyncClient")
    async def test_query_param_appends_jobs_keyword(self, mock_async_client):
        """Query string is built as '<query> jobs'."""
        from services.jobs_service import search_jobs

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"jobs_results": []}

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        await search_jobs("data scientist")

        call_kwargs = mock_client_instance.get.call_args[1]
        assert call_kwargs["params"]["q"] == "data scientist jobs"
        assert call_kwargs["params"]["engine"] == "google_jobs"
        assert call_kwargs["params"]["api_key"] == "test-api-key"

    @patch.dict("os.environ", {"SERPAPI_KEY": "test-api-key"})
    @patch("services.jobs_service.httpx.AsyncClient")
    async def test_raises_http_status_error_on_bad_response(self, mock_async_client):
        """API returns 4xx/5xx → raise_for_status propagates the exception."""
        from services.jobs_service import search_jobs

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Bad request", request=MagicMock(), response=MagicMock(status_code=400)
            )
        )

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(httpx.HTTPStatusError):
            await search_jobs("engineer")

    @patch.dict("os.environ", {"SERPAPI_KEY": "test-api-key"})
    @patch("services.jobs_service.httpx.AsyncClient")
    async def test_handles_missing_related_links_gracefully(self, mock_async_client):
        """Job with no related_links key → url defaults to empty string."""
        from services.jobs_service import search_jobs

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "jobs_results": [
                {
                    "job_id": "job-2",
                    "title": "Frontend Dev",
                    "company_name": "WebCo",
                    "location": "NYC",
                    "job_type": "Contract",
                    "description": "Build UIs",
                    # no related_links key at all
                }
            ]
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await search_jobs("frontend")

        assert result[0]["url"] == ""


# ===========================================================================
# get_linkedin_jobs_url()
# ===========================================================================


class TestGetLinkedInJobsUrl:
    def test_url_with_keywords_only(self):
        from services.jobs_service import get_linkedin_jobs_url
        url = get_linkedin_jobs_url("backend engineer")
        assert url == "https://www.linkedin.com/jobs/search/?keywords=backend%20engineer"

    def test_url_with_keywords_and_location(self):
        from services.jobs_service import get_linkedin_jobs_url
        url = get_linkedin_jobs_url("data scientist", location="New York")
        assert "keywords=data%20scientist" in url
        assert "location=New%20York" in url

    def test_url_without_location_omits_location_param(self):
        from services.jobs_service import get_linkedin_jobs_url
        url = get_linkedin_jobs_url("devops engineer")
        assert "location=" not in url

    def test_url_starts_with_base_linkedin_url(self):
        from services.jobs_service import get_linkedin_jobs_url
        url = get_linkedin_jobs_url("engineer")
        assert url.startswith("https://www.linkedin.com/jobs/search/")

    def test_url_with_none_location_explicit(self):
        from services.jobs_service import get_linkedin_jobs_url
        url = get_linkedin_jobs_url("engineer", location=None)
        assert "location=" not in url

    def test_url_with_single_word_keyword(self):
        from services.jobs_service import get_linkedin_jobs_url
        url = get_linkedin_jobs_url("python")
        assert "keywords=python" in url


# ===========================================================================
# get_internship_url()
# ===========================================================================


class TestGetInternshipUrl:
    def test_replaces_spaces_with_hyphens(self):
        from services.jobs_service import get_internship_url
        url = get_internship_url("software engineering intern")
        assert url == "https://www.internshala.com/jobs/search/software-engineering-intern"

    def test_single_word_keyword(self):
        from services.jobs_service import get_internship_url
        url = get_internship_url("python")
        assert url == "https://www.internshala.com/jobs/search/python"

    def test_starts_with_base_internshala_url(self):
        from services.jobs_service import get_internship_url
        url = get_internship_url("marketing intern")
        assert url.startswith("https://www.internshala.com/jobs/search/")

    def test_multiple_consecutive_spaces(self):
        from services.jobs_service import get_internship_url
        url = get_internship_url("data  science intern")
        # double space becomes double hyphen — documents actual behavior
        assert "data" in url and "science" in url and "intern" in url