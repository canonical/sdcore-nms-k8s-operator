#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module use to handle TLS certificates for the NMS."""

import logging
import socket
from typing import Optional

from charms.tls_certificates_interface.v4.tls_certificates import (
    Certificate,
    CertificateRequestAttributes,
    PrivateKey,
    TLSCertificatesRequiresV4,
)

logger = logging.getLogger(__name__)


CERTIFICATE_COMMON_NAME = "nms.sdcore"
TLS_RELATION_NAME = "certificates"
PRIVATE_KEY_PATH = "/support/TLS/nms.key"
CERTIFICATE_PATH = "/support/TLS/nms.pem"
CA_PATH = "/support/TLS/ca.pem"

class Tls:
    """Handle TLS certificates."""

    def __init__(self, charm, container):
        self._certificates = TLSCertificatesRequiresV4(
            charm=charm,
            relationship_name=TLS_RELATION_NAME,
            certificate_requests=[self._get_certificate_request()],
        )
        self._container = container

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
            self._store_ca(ca=provider_certificate.ca)
        if private_key_was_updated := self._is_private_key_update_required(private_key):
            self._store_private_key(private_key=private_key)
        return certificate_was_update or private_key_was_updated

    def _is_certificate_update_required(self, certificate: Certificate) -> bool:
        return self._get_existing_certificate() != certificate

    def _is_private_key_update_required(self, private_key: PrivateKey) -> bool:
        return self._get_existing_private_key() != private_key

    def _get_existing_certificate(self) -> Optional[Certificate]:
        return self._get_stored_certificate() if self._certificate_is_stored() else None

    def _get_existing_private_key(self) -> Optional[PrivateKey]:
        return self._get_stored_private_key() if self._private_key_is_stored() else None

    def _delete_certificate(self) -> None:
        if not self._certificate_is_stored():
            return
        self._container.remove_path(path=CERTIFICATE_PATH)
        logger.info("Removed certificate from workload")

    def _delete_private_key(self) -> None:
        if not self._private_key_is_stored():
            return
        self._container.remove_path(path=PRIVATE_KEY_PATH)
        logger.info("Removed private key from workload")

    def _get_stored_certificate(self) -> Certificate:
        cert_string = str(self._container.pull(path=CERTIFICATE_PATH).read())
        return Certificate.from_string(cert_string)

    def _get_stored_private_key(self) -> PrivateKey:
        key_string = str(self._container.pull(path=PRIVATE_KEY_PATH).read())
        return PrivateKey.from_string(key_string)

    def _certificate_is_stored(self) -> bool:
        return self._container.exists(path=CERTIFICATE_PATH)

    def _private_key_is_stored(self) -> bool:
        return self._container.exists(path=PRIVATE_KEY_PATH)

    def _store_certificate(self, certificate: Certificate) -> None:
        self._container.push(path=CERTIFICATE_PATH, source=str(certificate))
        logger.info("Pushed certificate to workload")

    def _store_private_key(self, private_key: PrivateKey) -> None:
        self._container.push(path=PRIVATE_KEY_PATH, source=str(private_key))
        logger.info("Pushed private key to workload")

    def _store_ca(self, ca: Certificate) -> None:
        self._container.push(path=CA_PATH, source=str(ca))
        logger.info("Pushed CA to workload")

    @staticmethod
    def _get_certificate_request() -> CertificateRequestAttributes:
        return CertificateRequestAttributes(
            common_name=CERTIFICATE_COMMON_NAME,
            sans_dns=frozenset([socket.getfqdn()]),
        )
