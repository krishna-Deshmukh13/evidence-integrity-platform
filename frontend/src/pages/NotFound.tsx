import { Link } from "react-router-dom";
import { Empty } from "@/components/ui";
export default function NotFound() { return <Empty title="Page not found" hint="That address does not exist." action={<Link className="text-accent" to="/">Go to the dashboard</Link>} />; }
