import Sidebar from "./Sidebar";

export default function PageShell({
  children,
  maxWidth = "max-w-6xl",
}: {
  children: React.ReactNode;
  maxWidth?: string;
}) {
  return (
    <div className="min-h-screen md:ml-60" style={{ background: "var(--mode-bg)" }}>
      <Sidebar />
      <div className={`mx-auto px-8 py-10 ${maxWidth}`}>{children}</div>
    </div>
  );
}
