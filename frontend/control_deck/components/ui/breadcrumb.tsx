import Link from "next/link"

export function Breadcrumb({ children }: { children: React.ReactNode }) {
  return (
    <nav aria-label="Breadcrumb" className="text-xs text-slate-400">
      {children}
    </nav>
  )
}

export function BreadcrumbList({ children }: { children: React.ReactNode }) {
  return <ol className="flex items-center gap-1">{children}</ol>
}

export function BreadcrumbItem({ children }: { children: React.ReactNode }) {
  return <li className="flex items-center gap-1">{children}</li>
}

export function BreadcrumbLink({
  href,
  children,
}: {
  href: string
  children: React.ReactNode
}) {
  return (
    <Link href={href} className="hover:text-slate-200">
      {children}
    </Link>
  )
}

export function BreadcrumbPage({ children }: { children: React.ReactNode }) {
  return <span className="font-medium text-slate-200">{children}</span>
}

export function BreadcrumbSeparator({
  className,
}: {
  className?: string
}) {
  return <span className={className}>/</span>
}