// Display gate only. The API remains the authorization authority on every request.
export function hasAdministratorAccess(state: string, role: string | null | undefined, mfaVerified: boolean) {
  return state === "authenticated"
    && (role === "ADMIN" || role === "SUPER_ADMIN")
    && mfaVerified === true;
}
