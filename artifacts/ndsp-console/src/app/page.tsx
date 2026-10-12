import type { Metadata } from "next";
import CommandCenter from "../components/CommandCenter";
import PageFrame from "../components/PageFrame";

export const metadata: Metadata = { title: "Command Center", description: "NAWAF M1 identity, service health and safety boundaries. No trading data." };

export default function Home() {
  return <PageFrame title="Command Center" description="Identity, service health and M1 safety boundaries."><CommandCenter /></PageFrame>;
}