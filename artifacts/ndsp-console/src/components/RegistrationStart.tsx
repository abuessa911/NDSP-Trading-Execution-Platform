/** Native anchor works without hydration, fetch, or browser JavaScript.
 * The server generates signed-by-flow state, nonce and PKCE before redirecting.
 */
export default function RegistrationStart() {
  return <a className="hunter-primary-link" href="/api/v1/auth/start?register=true">إنشاء الحساب والتحقق من البريد ←</a>;
}
