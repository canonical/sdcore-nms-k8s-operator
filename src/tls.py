#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module use to handle TLS certificates for the NMS."""

import logging
from typing import Optional

from charms.tls_certificates_interface.v4.tls_certificates import (
    Certificate,
    CertificateRequestAttributes,
    PrivateKey,
    TLSCertificatesRequiresV4,
)
from ops import CharmBase, Container

logger = logging.getLogger(__name__)


CERTIFICATE_COMMON_NAME = "nms.sdcore"
PRIVATE_KEY_NAME = "nms.key"
CERTIFICATE_NAME = "nms.pem"
CA_CERTIFICATE_NAME = "ca.pem"


class Tls:
    """Handle TLS certificates."""

    def __init__(
            self,
            charm: CharmBase,
            relation_name: str,
            container: Container,
            domain_name: str,
            storage_path: str
        ):
        self._storage_path = storage_path
        self._domain_name = domain_name
        self._container = container
        self._certificates = TLSCertificatesRequiresV4(
            charm=charm,
            relationship_name=relation_name,
            certificate_requests=[self._get_certificate_request()],
        )

    def certificate_is_available(self) -> bool:
        cert, key = self._certificates.get_assigned_certificate(
            certificate_request=self._get_certificate_request()
        )
        return bool(cert and key)

    def check_and_update_certificate(self) -> bool:
        """Check if the certificate or private key needs an update and perform the update.

        This method retrieves the currently assigned certificate and private key associated with
        the charm's TLS relation. It checks whether the certificate or private key has changed
        or needs to be updated. If an update is necessary, the new certificate or private key is
        stored.

        Returns:
            bool: True if either the certificate or the private key was updated, False otherwise.
        """
        provider_certificate, private_key = self._certificates.get_assigned_certificate(
            certificate_request=self._get_certificate_request()
        )
        if not provider_certificate or not private_key:
            logger.debug("Certificate or private key is not available")
            return False
        if certificate_was_update := self._is_certificate_update_required(
            provider_certificate.certificate
        ):
            self._store_certificate(certificate=provider_certificate.certificate)
        if ca_certificate_was_update := self._is_ca_certificate_update_required(
            provider_certificate.ca
        ):
            self._store_ca_certificate(ca=provider_certificate.ca)
        if private_key_was_updated := self._is_private_key_update_required(private_key):
            self._store_private_key(private_key=private_key)
        return certificate_was_update or private_key_was_updated or ca_certificate_was_update

    def clean_up_certificates(self) -> None:
        self._delete_private_key()
        self._delete_certificate()
        self._delete_ca_certificate()

    def _is_certificate_update_required(self, certificate: Certificate) -> bool:
        return self._get_existing_certificate() != certificate

    def _is_private_key_update_required(self, private_key: PrivateKey) -> bool:
        return self._get_existing_private_key() != private_key

    def _is_ca_certificate_update_required(self, certificate: Certificate) -> bool:
        return self._get_existing_ca_certificate() != certificate

    def _get_existing_certificate(self) -> Optional[Certificate]:
        return self._get_stored_certificate() if self._certificate_is_stored() else None

    def _get_existing_private_key(self) -> Optional[PrivateKey]:
        return self._get_stored_private_key() if self._private_key_is_stored() else None

    def _get_existing_ca_certificate(self) -> Optional[Certificate]:
        return self._get_stored_ca_certificate() if self._ca_certificate_is_stored() else None

    def _delete_certificate(self) -> None:
        if not self._certificate_is_stored():
            return
        self._container.remove_path(path=self.certificate_workload_path)
        logger.info("Removed certificate from workload")

    def _delete_private_key(self) -> None:
        if not self._private_key_is_stored():
            return
        self._container.remove_path(path=self.private_key_workload_path)
        logger.info("Removed private key from workload")

    def _delete_ca_certificate(self) -> None:
        if not self._ca_certificate_is_stored():
            return
        self._container.remove_path(path=self.ca_certificate_workload_path)
        logger.info("Removed CA certificate from workload")

    def _get_stored_certificate(self) -> Certificate:
        cert_string = str(self._container.pull(path=self.certificate_workload_path).read())
        return Certificate.from_string(cert_string)

    def _get_stored_private_key(self) -> PrivateKey:
        key_string = str(self._container.pull(path=self.private_key_workload_path).read())
        return PrivateKey.from_string(key_string)

    def _get_stored_ca_certificate(self) -> Certificate:
        cert_string = str(self._container.pull(path=self.ca_certificate_workload_path).read())
        return Certificate.from_string(cert_string)

    def _certificate_is_stored(self) -> bool:
        return self._container.exists(path=self.certificate_workload_path)

    def _private_key_is_stored(self) -> bool:
        return self._container.exists(path=self.private_key_workload_path)

    def _ca_certificate_is_stored(self) -> bool:
        return self._container.exists(path=self.ca_certificate_workload_path)

    def _store_certificate(self, certificate: Certificate) -> None:
        self._container.push(path=self.certificate_workload_path, source=str(certificate))
        logger.info("Pushed certificate to workload")

    def _store_private_key(self, private_key: PrivateKey) -> None:
        self._container.push(path=self.private_key_workload_path, source=str(private_key))
        logger.info("Pushed private key to workload")

    def _store_ca_certificate(self, ca: Certificate) -> None:
        self._container.push(path=self.ca_certificate_workload_path, source=str(ca))
        logger.info("Pushed CA certificate to workload")

    def _get_certificate_request(self) -> CertificateRequestAttributes:
        return CertificateRequestAttributes(
            common_name=CERTIFICATE_COMMON_NAME,
            sans_dns=frozenset([self._domain_name]),
        )

    @property
    def certificate_workload_path(self) -> str:
        return f"{self._storage_path}/{CERTIFICATE_NAME}"

    @property
    def private_key_workload_path(self) -> str:
        return f"{self._storage_path}/{PRIVATE_KEY_NAME}"

    @property
    def ca_certificate_workload_path(self) -> str:
        return f"{self._storage_path}/{CA_CERTIFICATE_NAME}"
