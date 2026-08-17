#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log_info() {
    printf "\033[0;32m[%s] [INFO] %s\033[0m\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

log_warn() {
    printf "\033[0;33m[%s] [WARN] %s\033[0m\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

log_error() {
    printf "\033[0;31m[%s] [ERROR] %s\033[0m\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2
}

check_python() {
    if ! command -v python3 >/dev/null 2>&1; then
        log_error "python3 is not available in PATH"
        exit 2
    fi
}

check_disk_space() {
    local free_kb
    free_kb=$(df -Pk "${PROJECT_ROOT}" 2>/dev/null | awk 'NR==2 {print $4}' || true)
    if [[ -n "${free_kb}" && "${free_kb}" =~ ^[0-9]+$ ]]; then
        if (( free_kb < 102400 )); then
            log_warn "Low disk space: less than 100MB free (${free_kb} KB remaining)"
        fi
    fi
}

check_permissions() {
    local dir
    for dir in "${PROJECT_ROOT}/data" "${PROJECT_ROOT}/logs"; do
        if [[ ! -d "${dir}" ]]; then
            if ! mkdir -p "${dir}" 2>/dev/null; then
                log_error "Failed to create directory: ${dir}"
                exit 2
            fi
        fi
        if [[ ! -w "${dir}" ]]; then
            log_error "Directory is not writable: ${dir}"
            exit 2
        fi
    done
}

main() {
    log_info "Migration Toolkit v1.0.0"

    check_python
    check_disk_space
    check_permissions

    cd "${PROJECT_ROOT}"

    local exit_code=0
    python3 -m migration_toolkit.migrator || exit_code=$?

    case "${exit_code}" in
        0)
            log_info "Migration completed successfully"
            ;;
        1)
            log_warn "Migration failed partway. Run rollback: python3 -m migration_toolkit.rollback"
            ;;
        2)
            log_error "Fatal error during migration"
            ;;
        *)
            log_error "Fatal error during migration"
            ;;
    esac

    exit "${exit_code}"
}

main "$@"
