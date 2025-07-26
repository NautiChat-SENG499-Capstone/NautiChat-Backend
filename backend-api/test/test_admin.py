import io
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.admin.models import VectorDocument
from src.auth import schemas
from src.auth.service import get_user_by_token
from src.settings import get_settings


class TestAuthentication:
    @pytest.mark.asyncio
    async def test_admin_endpoint_unauthenticated(self, client: AsyncClient):
        """Test attempt at accessing admin endpoint"""
        response = await client.get("/admin/messages")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_admin_endpoint_as_user(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test attempt at accessing admin endpoint with user account"""
        response = await client.get("/admin/messages", headers=user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAdminCreation:
    def _create_user_request(
        self,
        username: str = "tester",
        password: str = "password",
        token=get_settings().ONC_TOKEN,
    ) -> schemas.CreateUserRequest:
        """Create User Request schema"""
        user = schemas.CreateUserRequest(
            username=username, password=password, onc_token=token
        )
        return user

    @pytest.mark.asyncio
    async def test_create_admin_success(self, client: AsyncClient, admin_headers: dict):
        """Test attempt at creating new admin"""
        new_admin = self._create_user_request(
            username="newadmin", password="securepass123"
        )

        response = await client.post(
            "/admin/create", json=new_admin.model_dump(), headers=admin_headers
        )
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["username"] == new_admin.username
        assert data["is_admin"] is True

    @pytest.mark.asyncio
    async def test_create_admin_unauthenticated(self, client: AsyncClient):
        """Test attempt create admin without authentication"""
        bad_request = self._create_user_request(username="unauth", password="x")
        response = await client.post(
            "/admin/create",
            json=bad_request.model_dump(),
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_admin_as_normal_user(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test attempt at creating admin as normal user"""
        bad_request = self._create_user_request(username="baduser", password="x")
        response = await client.post(
            "/admin/create",
            json=bad_request.model_dump(),
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_create_admin_invalid_onc_token(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Test creating an admin with an invalid ONC token"""
        invalid_admin = self._create_user_request(
            username="admin4", password="pass", token="invalid_token"
        )
        response = await client.post(
            "/admin/create",
            json=invalid_admin.model_dump(),
            headers=admin_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Invalid ONC token"


class TestDeleteUsers:
    @pytest.mark.asyncio
    async def test_delete_admin_user_success(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Test that deletes admin user from db"""
        target_admin_data = {
            "username": "deleteadmin",
            "password": "deletepass",
            "onc_token": get_settings().ONC_TOKEN,
        }

        create_response = await client.post(
            "/admin/create", json=target_admin_data, headers=admin_headers
        )
        assert create_response.status_code == status.HTTP_201_CREATED

        target_id = create_response.json()["id"]

        delete_response = await client.delete(
            f"/admin/users/{target_id}", headers=admin_headers
        )
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_admin_cannot_delete_self(
        self, client: AsyncClient, async_session: AsyncSession, admin_headers: dict
    ):
        """Test that attempts for admin to delete themselves"""
        # Extract the token from headers
        token = admin_headers["Authorization"].split("Bearer ")[1]

        # Get user object
        admin_user = await get_user_by_token(token, get_settings(), async_session)

        response = await client.delete(
            f"/admin/users/{admin_user.id}", headers=admin_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            response.json()["detail"] == "Admins are not allowed to delete themselves"
        )


class TestMessageClustering:
    @pytest.mark.asyncio
    async def test_clustered_messages_returns_valid_json(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Test that clusters messages"""
        response = await client.get("/admin/messages/clustered", headers=admin_headers)

        assert response.status_code == status.HTTP_200_OK
        clusters = response.json()
        assert isinstance(clusters, dict)


class TestAdminDocumentUpload:
    @patch("src.admin.service.raw_text_upload_to_vdb", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_upload_raw_text_success(self, mock_upload, client, admin_headers):
        """Test that upload raw text returns 201 on success"""
        mock_upload.return_value = None
        resp = await client.post(
            "/admin/documents/raw-data",
            headers=admin_headers,
            data={"source": "mysource", "input_text": "hello world"},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["detail"] == "Raw text uploaded successfully"
        mock_upload.assert_awaited_once()

    @patch("src.admin.service.raw_text_upload_to_vdb", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_upload_raw_text_failure(self, mock_upload, client, admin_headers):
        """Test that upload raw text returns 500 on failure"""
        mock_upload.side_effect = HTTPException(
            status_code=502, detail="Simulated failure"
        )
        resp = await client.post(
            "/admin/documents/raw-data",
            headers=admin_headers,
            data={"source": "mysource", "input_text": "hello world"},
        )
        assert resp.status_code >= 500

    @patch(
        "src.admin.service.prepare_embedding_input_from_preformatted",
        new_callable=AsyncMock,
    )
    @patch("src.admin.service.upload_to_vector_db", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_raw_text_creates_metadata(
        self,
        mock_vec_upload,
        mock_prepare,
        client,
        admin_headers,
        async_session,
    ):
        """Test that raw text upload creates metadata in vector DB"""
        mock_prepare.return_value = "prepared"
        mock_vec_upload.return_value = None

        resp = await client.post(
            "/admin/documents/raw-data",
            headers=admin_headers,
            data={"source": "raw_success_doc", "input_text": "hello DB!"},
        )

        assert resp.status_code == 201
        # row should exist

        row = await async_session.scalar(
            select(VectorDocument).where(VectorDocument.source == "raw_success_doc")
        )
        assert row is not None

    @patch(
        "src.admin.service.prepare_embedding_input_from_preformatted", new_callable=Mock
    )
    @patch("src.admin.service.upload_to_vector_db", new_callable=Mock)
    @pytest.mark.asyncio
    async def test_raw_text_rolls_back_on_failure(
        self,
        mock_vec_upload,
        mock_prepare,
        client,
        admin_headers,
        async_session,
    ):
        """Test that raw text upload rolls back on failure"""
        mock_prepare.return_value = "prepared"
        mock_vec_upload.side_effect = Exception("boom")

        resp = await client.post(
            "/admin/documents/raw-data",
            headers=admin_headers,
            data={"source": "raw_fail_doc", "input_text": "will roll back"},
        )

        assert resp.status_code >= 500
        # verify row was removed
        row = await async_session.scalar(
            select(VectorDocument).where(VectorDocument.source == "raw_fail_doc")
        )
        assert row is None

    @patch("src.admin.service.pdf_upload_to_vdb", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_upload_pdf_success(self, mock_upload, client, admin_headers):
        """Test that upload PDF returns 202 on success"""
        mock_upload.return_value = None
        pdf_bytes = io.BytesIO(b"%PDF-1.4 test content")
        resp = await client.post(
            "/admin/documents/pdf",
            headers=admin_headers,
            files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
            data={"source": "pdfsource"},
        )
        assert resp.status_code == status.HTTP_202_ACCEPTED
        assert resp.json()["detail"] == "PDF upload queued for processing."
        mock_upload.assert_called_once()


class TestAdminDocumentCRUD:
    @patch("src.admin.service.get_all_documents", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_get_all_documents_success(self, mock_get_all, client, admin_headers):
        """Test that get all documents returns metadata"""
        # Return a list of document dicts as VectorDocumentOut expects
        mock_get_all.return_value = [
            {"id": 1, "source": "foo", "usage_count": 5, "uploaded_by_id": 1}
        ]
        resp = await client.get("/admin/documents", headers=admin_headers)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["source"] == "foo"
        mock_get_all.assert_awaited_once()

    @patch("src.admin.service.get_all_documents", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_get_all_documents_failure(self, mock_get_all, client, admin_headers):
        """Test that get all documents returns 500 on failure"""
        mock_get_all.side_effect = HTTPException(status_code=500, detail="fail")
        resp = await client.get("/admin/documents", headers=admin_headers)
        assert resp.status_code == 500
        assert resp.json()["detail"] == "fail"

    @patch("src.admin.service.get_document_by_source", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_get_document_by_source_success(
        self, mock_get_one, client, admin_headers
    ):
        """Test that get document by source returns metadata"""
        mock_get_one.return_value = {
            "id": 2,
            "source": "mysource",
            "usage_count": 1,
            "uploaded_by_id": 7,
        }
        resp = await client.get("/admin/documents/mysource", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "mysource"
        # Check mock was called with correct arguments
        called_args = mock_get_one.await_args.args
        assert called_args[0] == "mysource"
        assert isinstance(called_args[1], AsyncSession)

    @patch("src.admin.service.get_document_by_source", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_get_document_by_source_not_found(
        self, mock_get_one, client, admin_headers
    ):
        """Test that get document by source returns 404 when not found"""
        mock_get_one.side_effect = HTTPException(status_code=404, detail="not found")
        resp = await client.get("/admin/documents/doesnotexist", headers=admin_headers)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "not found"

    @patch("src.admin.service.source_remove_from_vdb", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_delete_document_success(self, mock_remove, client, admin_headers):
        """Test that delete document removes from vector DB"""
        mock_remove.return_value = None
        resp = await client.delete("/admin/documents/toremove", headers=admin_headers)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        mock_remove.assert_awaited_once()

    @patch("src.admin.service.source_remove_from_vdb", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_delete_document_failure(self, mock_remove, client, admin_headers):
        """Test that delete document returns 500 on failure"""
        mock_remove.side_effect = HTTPException(status_code=500, detail="fail")
        resp = await client.delete("/admin/documents/toremove", headers=admin_headers)
        assert resp.status_code == 500
        assert resp.json()["detail"] == "fail"
