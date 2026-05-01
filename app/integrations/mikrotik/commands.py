def build_new_cert_command(
    cert_id: int,
) -> str:

    return (
        f':global newCertId "{cert_id}";/system script run newCertId; '
    )


def build_disable_cert_command(
    cert_id: list[int],
) -> str:

    certs = ",".join(
        str(cert_id)
        for cert_id in cert_ids
    )

    return (
        f':global stopCerts "{cert_id}";/system script run disableCertId;'
    )


def build_renew_cert_command(
    cert_id: int,
) -> str:

    return (
        f':global certId "{cert_id}";/system script run reNewCertId;'
    )

def build_remove_file_command(
    cert_id: int,
) -> str:

    return (
        f'/file remove "{cert_id}.p12"'
    )
