import type { Metadata } from "next";
import { PublicLoginRedirect } from "../../components/PublicEntry";
export const metadata: Metadata = { title: "الدخول الآمن | Secure sign in — HUNTER KSA1" };
export default function Login() { return <PublicLoginRedirect/>; }
