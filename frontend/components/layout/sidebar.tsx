"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  Bell,
  Bot,
  CalendarClock,
  CalendarDays,
  CalendarPlus2,
  CircleDollarSign,
  FileText,
  LayoutDashboard,
  ScrollText,
  Ticket,
  UserCircle2,
  Users,
  Vote,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/dashboard" },
  { icon: Bot, label: "AI Copilot", href: "/copilot" },
  {
    icon: Activity,
    label: "AI Usage",
    href: "/ai-usage",
    adminOnly: true,
  },
  { icon: Users, label: "Employees", href: "/employees" },
  { icon: UserCircle2, label: "My Profile", href: "/me" },
  { icon: FileText, label: "My Documents", href: "/me/documents" },
  { icon: CircleDollarSign, label: "Finance", href: "/finance" },
  { icon: CalendarClock, label: "Attendance", href: "/attendance" },
  { icon: CalendarPlus2, label: "Leaves", href: "/leaves" },
  { icon: Bell, label: "Announcements", href: "/announcements" },
  { icon: ScrollText, label: "HR Policies", href: "/hr-policies" },
  
  { icon: Vote, label: "Polls", href: "/polls" },
  { icon: CalendarDays, label: "Team Calendar", href: "/team-calendar" },
  { icon: Ticket, label: "Tickets", href: "/tickets" },
];

export function Sidebar() {
  const pathname = usePathname();
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    try {
      const accessToken = localStorage.getItem("hrms_access_token");

      let tokenRole = "";

      if (accessToken) {
        const tokenParts = accessToken.split(".");

        if (tokenParts.length === 3) {
          const payload = JSON.parse(atob(tokenParts[1]));
          tokenRole = String(
            payload.role ?? payload.role_name ?? ""
          ).toUpperCase();
        }
      }

      // Prefer the role in the access token. Use the cookie as a fallback.
      let cookieRole = "";

      if (typeof document !== "undefined") {
        const roleCookie = document.cookie
          .split("; ")
          .find((cookie) => cookie.startsWith("hrms_role="));

        if (roleCookie) {
          cookieRole = decodeURIComponent(
            roleCookie.substring("hrms_role=".length)
          ).toUpperCase();
        }
      }

      setIsAdmin(tokenRole ? tokenRole === "ADMIN" : cookieRole === "ADMIN");
    } catch (error) {
      console.error("Unable to determine user role for sidebar:", error);
      setIsAdmin(false);
    }
  }, []);

  const visibleNavItems = navItems.filter(
    (item) => !("adminOnly" in item && item.adminOnly) || isAdmin
  );

  return (
    <aside className="hidden w-72 border-r border-slate-900/80 bg-gradient-to-b from-[#0f1b33] via-[#0c1730] to-[#081121] md:block">
      <div className="border-b border-white/5 px-4 pb-4 pt-6 text-center">
        <div className="mx-auto h-20 w-56 overflow-hidden">
          <Image
            src="/logo.png"
            alt="HRMS Logo"
            width={320}
            height={120}
            className="h-full w-full object-cover object-center"
            priority
          />
        </div>
      </div>

      <nav className="space-y-1 px-3 py-4">
        {visibleNavItems.map((item) => (
          <Link
            key={item.label}
            href={item.href}
            className={cn(
              "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-300 transition hover:bg-white/5 hover:text-white",
              item.href !== "#" &&
                pathname.startsWith(item.href) &&
                "bg-gradient-to-r from-indigo-500/20 to-transparent text-white ring-1 ring-indigo-400/20"
            )}
          >
            <span
              className={cn(
                "inline-flex h-8 w-8 items-center justify-center rounded-lg bg-transparent transition group-hover:bg-white/5",
                item.href !== "#" &&
                  pathname.startsWith(item.href) &&
                  "bg-indigo-400/10"
              )}
            >
              <item.icon className="h-4 w-4" />
            </span>

            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}