#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
METADATA="$(python3 -c "
import re
with open('${ROOT_DIR}/pyproject.toml') as f:
    content = f.read()
version = re.search(r'version\s*=\s*\"([^\"]+)\"', content).group(1)
desc = re.search(r'description\s*=\s*\"([^\"]+)\"', content).group(1)
print(version)
print(desc)
")"
VERSION="$(echo "${METADATA}" | head -n1)"
DESCRIPTION="$(echo "${METADATA}" | tail -n+2)"
PACKAGE_NAME="gx"
ARCHITECTURE="${DEB_ARCHITECTURE:-all}"
MAINTAINER="${DEB_MAINTAINER:-Guruswarupa <opensource@local.invalid>}"
OUTPUT_DIR="${ROOT_DIR}/dist"
BUILD_ROOT="$(mktemp -d)"
PACKAGE_ROOT="${BUILD_ROOT}/${PACKAGE_NAME}_${VERSION}"
INSTALL_ROOT="${PACKAGE_ROOT}/usr/lib/${PACKAGE_NAME}"
CONTROL_DIR="${PACKAGE_ROOT}/DEBIAN"
DOC_DIR="${PACKAGE_ROOT}/usr/share/doc/${PACKAGE_NAME}"
DEB_FILE="${OUTPUT_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCHITECTURE}.deb"

cleanup() {
  rm -rf "${BUILD_ROOT}"
}

trap cleanup EXIT

mkdir -p "${OUTPUT_DIR}" "${INSTALL_ROOT}" "${CONTROL_DIR}" "${DOC_DIR}" "${PACKAGE_ROOT}/usr/bin"

cp -a \
  "${ROOT_DIR}/gx" \
  "${ROOT_DIR}/README.md" \
  "${INSTALL_ROOT}/"

cat > "${PACKAGE_ROOT}/usr/bin/gx" <<EOF
#!/bin/sh
PYTHONPATH="/usr/lib/${PACKAGE_NAME}" exec python3 -m gx.cli "\$@"
EOF
chmod 755 "${PACKAGE_ROOT}/usr/bin/gx"
ln -s "gx" "${PACKAGE_ROOT}/usr/bin/gitxplain"

find "${PACKAGE_ROOT}" -type d -exec chmod 755 {} +
find "${PACKAGE_ROOT}" -type f -exec chmod 644 {} +
chmod 755 "${PACKAGE_ROOT}/usr/bin/gx"

cat > "${CONTROL_DIR}/control" <<EOF
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCHITECTURE}
Maintainer: ${MAINTAINER}
Depends: python3 (>= 3.8), python3-requests
Homepage: https://github.com/guruswarupa/gitxplain
Description: ${DESCRIPTION}
 AI-powered Git commit explainer CLI distributed as a Debian package.
EOF

cat > "${DOC_DIR}/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: gitxplain
Source: https://github.com/guruswarupa/gitxplain

Files: *
License: MIT
EOF

dpkg-deb --root-owner-group --build "${PACKAGE_ROOT}" "${DEB_FILE}" >/dev/null
echo "${DEB_FILE}"
