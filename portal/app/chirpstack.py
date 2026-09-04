"""ChirpStack v4 gRPC client for the LoRa track (M4.1).

ChirpStack's API is gRPC (the Login RPC has no REST mapping), so we use the official chirpstack-api
stubs against chirpstack:8080. Bootstraps a shared tenant, application, device profile and an admin
API key; registers OTAA devices. Internal network only."""

from __future__ import annotations

import os
import secrets

import grpc
from chirpstack_api import api
from chirpstack_api.api import (
    application_pb2,
    device_pb2,
    device_profile_pb2,
    internal_pb2,
    tenant_pb2,
)
from chirpstack_api.common import common_pb2

GRPC = os.environ.get("CHIRPSTACK_GRPC", "chirpstack:8080")
TENANT_NAME = "CHERT IoT"
APP_NAME = "chertiot"
PROFILE_NAME = "chertiot-eu868-otaa"


def _channel() -> grpc.Channel:
    return grpc.insecure_channel(GRPC)


def login_admin(email: str = "admin", password: str = "admin") -> str:  # noqa: S107
    """Default ChirpStack admin exists on a fresh instance; used once to mint an API key."""
    stub = api.InternalServiceStub(_channel())
    resp = stub.Login(internal_pb2.LoginRequest(email=email, password=password))
    return str(resp.jwt)


class ChirpStack:
    def __init__(self, token: str) -> None:
        self._ch = _channel()
        self._auth = [("authorization", f"Bearer {token}")]

    # --- bootstrap ---------------------------------------------------------------
    def ensure_tenant(self) -> str:
        stub = api.TenantServiceStub(self._ch)
        listed = stub.List(tenant_pb2.ListTenantsRequest(limit=100), metadata=self._auth)
        for t in listed.result:
            if t.name == TENANT_NAME:
                return str(t.id)
        tenant = tenant_pb2.Tenant(name=TENANT_NAME, can_have_gateways=True)
        return str(
            stub.Create(tenant_pb2.CreateTenantRequest(tenant=tenant), metadata=self._auth).id
        )

    def create_admin_api_key(self) -> str:
        stub = api.InternalServiceStub(self._ch)
        key = internal_pb2.ApiKey(name="chertiot-portal", is_admin=True)
        resp = stub.CreateApiKey(internal_pb2.CreateApiKeyRequest(api_key=key), metadata=self._auth)
        return str(resp.token)

    def ensure_application(self, tenant_id: str) -> str:
        stub = api.ApplicationServiceStub(self._ch)
        listed = stub.List(
            application_pb2.ListApplicationsRequest(limit=100, tenant_id=tenant_id),
            metadata=self._auth,
        )
        for a in listed.result:
            if a.name == APP_NAME:
                return str(a.id)
        app = application_pb2.Application(
            name=APP_NAME, description="CHERT IoT student LoRa devices", tenant_id=tenant_id
        )
        return str(
            stub.Create(
                application_pb2.CreateApplicationRequest(application=app), metadata=self._auth
            ).id
        )

    def ensure_device_profile(self, tenant_id: str) -> str:
        stub = api.DeviceProfileServiceStub(self._ch)
        listed = stub.List(
            device_profile_pb2.ListDeviceProfilesRequest(limit=100, tenant_id=tenant_id),
            metadata=self._auth,
        )
        for p in listed.result:
            if p.name == PROFILE_NAME:
                return str(p.id)
        profile = device_profile_pb2.DeviceProfile(
            tenant_id=tenant_id,
            name=PROFILE_NAME,
            region=common_pb2.EU868,
            mac_version=common_pb2.LORAWAN_1_0_3,
            reg_params_revision=common_pb2.A,
            adr_algorithm_id="default",
            uplink_interval=3600,
            supports_otaa=True,
            flush_queue_on_activate=True,
        )
        return str(
            stub.Create(
                device_profile_pb2.CreateDeviceProfileRequest(device_profile=profile),
                metadata=self._auth,
            ).id
        )

    # --- devices -----------------------------------------------------------------
    def create_device(
        self, app_id: str, profile_id: str, dev_eui: str, name: str, app_key: str
    ) -> None:
        stub = api.DeviceServiceStub(self._ch)
        device = device_pb2.Device(
            dev_eui=dev_eui, name=name, application_id=app_id, device_profile_id=profile_id
        )
        stub.Create(device_pb2.CreateDeviceRequest(device=device), metadata=self._auth)
        keys = device_pb2.DeviceKeys(dev_eui=dev_eui, nwk_key=app_key, app_key=app_key)
        stub.CreateKeys(device_pb2.CreateDeviceKeysRequest(device_keys=keys), metadata=self._auth)

    def delete_device(self, dev_eui: str) -> None:
        api.DeviceServiceStub(self._ch).Delete(
            device_pb2.DeleteDeviceRequest(dev_eui=dev_eui), metadata=self._auth
        )


def new_dev_eui() -> str:
    return secrets.token_hex(8)


def new_app_key() -> str:
    return secrets.token_hex(16)
