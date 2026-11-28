import { AdminLoginClient } from "@/components/admin/AdminLoginClient";

export const metadata = {
  title: "Вход — статистика",
  robots: { index: false, follow: false },
};

export default function AdminLoginPage() {
  return <AdminLoginClient />;
}