'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import Link from 'next/link';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout, fetchUser } = useAuthStore();
  const [showUsageLimitModal, setShowUsageLimitModal] = useState(false);
  const [showBannedModal, setShowBannedModal] = useState(false);
  const [usageLimitData, setUsageLimitData] = useState<any>(null);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/auth/login');
    }
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    const handleUsageLimitExceeded = (event: any) => {
      setUsageLimitData(event.detail);
      setShowUsageLimitModal(true);
    };

    const handleUserBanned = () => {
      setShowBannedModal(true);
      setTimeout(() => {
        logout();
      }, 3000);
    };

    window.addEventListener('usage-limit-exceeded', handleUsageLimitExceeded);
    window.addEventListener('user-banned', handleUserBanned);

    return () => {
      window.removeEventListener('usage-limit-exceeded', handleUsageLimitExceeded);
      window.removeEventListener('user-banned', handleUserBanned);
    };
  }, [logout]);

  const handleLogout = async () => {
    await logout();
    router.push('/auth/login');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-gap-lg py-gap-md flex items-center justify-between">
          <Link href="/dashboard" className="text-2xl font-semibold tracking-tight text-gray-900">
            アビトラ⚡
          </Link>
          <div className="flex items-center gap-gap-md">
            <span className="text-sm text-muted">{user?.display_name}</span>
            <button
              onClick={handleLogout}
              className="text-sm text-primary-500 hover:text-primary-600 hover:opacity-80 transition-opacity font-medium"
            >
              ログアウト
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-gap-lg py-gap-lg">
        <div className="flex gap-gap-lg">
          {/* Sidebar */}
          <aside className="w-64 flex-shrink-0">
            <nav className="space-y-gap-xs">
              <Link
                href="/dashboard"
                className="block px-gap-md py-gap-sm rounded-lg hover:bg-gray-100 text-gray-900 font-medium"
              >
                分析
              </Link>
              <Link
                href="/dashboard/games"
                className="block px-gap-md py-gap-sm rounded-lg hover:bg-gray-100 text-gray-900 font-medium"
              >
                今日の試合
              </Link>
              <Link
                href="/dashboard/settings"
                className="block px-gap-md py-gap-sm rounded-lg hover:bg-gray-100 text-gray-900 font-medium"
              >
                設定
              </Link>
              <Link
                href="/dashboard/subscription"
                className="block px-gap-md py-gap-sm rounded-lg hover:bg-gray-100 text-gray-900 font-medium"
              >
                サブスクリプション
              </Link>
            </nav>
          </aside>

          {/* Main Content */}
          <main className="flex-1">{children}</main>
        </div>
      </div>

      {/* Usage Limit Modal */}
      {showUsageLimitModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-gap-xl max-w-md mx-gap-md">
            <h2 className="text-xl font-semibold tracking-tight text-gray-900 mb-gap-md">
              利用上限に達しました
            </h2>
            <p className="text-muted mb-gap-lg">
              {usageLimitData?.detail || '今月の利用回数が上限に達しました。Proプランにアップグレードして無制限に利用できます。'}
            </p>
            <div className="flex gap-gap-md">
              <button
                onClick={() => setShowUsageLimitModal(false)}
                className="flex-1 px-gap-md py-gap-sm rounded-lg border border-gray-300 text-gray-900 hover:bg-gray-50"
              >
                閉じる
              </button>
              <Link
                href="/dashboard/subscription"
                onClick={() => setShowUsageLimitModal(false)}
                className="flex-1 px-gap-md py-gap-sm rounded-lg bg-primary-500 text-white text-center hover:bg-primary-600"
              >
                プラン確認
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Banned Modal */}
      {showBannedModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-gap-xl max-w-md mx-gap-md">
            <h2 className="text-xl font-semibold tracking-tight text-danger-600 mb-gap-md">
              アカウントが停止されました
            </h2>
            <p className="text-muted mb-gap-lg">
              お使いのアカウントは管理者により停止されました。詳細については運営にお問い合わせください。
            </p>
            <p className="text-sm text-muted">
              3秒後に自動的にログアウトします...
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
