import type { Metadata } from "next";
import PublicWelcome from "../components/PublicEntry";
export const metadata: Metadata = { title: "HUNTER KSA1 | Home", description: "Hunter trading platform" };
export default function Home() { return <PublicWelcome/>; }
