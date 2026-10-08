"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  ["/", "Overview"],
  ["/world", "World viewer"],
  ["/evolution", "Evolution explorer"],
  ["/designer", "Experiment designer"],
  ["/benchmark", "Benchmark analysis"],
  ["/artifacts", "Artifacts"],
  ["/failures", "Failures"],
] as const;

export default function Nav() {
  const path = usePathname();
  return (
    <nav>
      {LINKS.map(([href, label]) => (
        <Link key={href} href={href} className={path === href ? "active" : ""}>
          {label}
        </Link>
      ))}
    </nav>
  );
}
