import Sidebar from "./Sidebar";

export default function PageShell({
  children,
  maxWidth = "max-w-6xl",
}: {
  children: React.ReactNode;
  maxWidth?: string;
}) {
  return (
    <div className="min-h-screen bg-gray-50 md:ml-60">
      <Sidebar />
      <div className={`mx-auto px-8 py-8 ${maxWidth}`}>{children}</div>
    </div>
  );
}
