import Link from "next/link";

const routes = ["/device", "/ops", "/log", "/sheets"];

export default function Home() {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">となり</h1>
      <ul className="mt-4 space-y-2">
        {routes.map((href) => (
          <li key={href}>
            <Link href={href} className="underline">
              {href}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
