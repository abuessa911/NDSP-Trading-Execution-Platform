import type { Metadata } from "next";
import { BOT_NAME } from "../../lib/bot-profile";
import CommandCenter from "../../components/CommandCenter";
import PageFrame from "../../components/PageFrame";
export const metadata: Metadata = { title: "Command Center", description: `${BOT_NAME} service status and safety boundaries.` };
export default function Dashboard() {
  return <PageFrame title="Command Center" description="Identity, service health and M1 safety boundaries."><CommandCenter /></PageFrame>;
}
