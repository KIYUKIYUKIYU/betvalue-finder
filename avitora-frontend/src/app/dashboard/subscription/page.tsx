'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/store/authStore';
import apiClient from '@/lib/api';
import { useRouter } from 'next/navigation';

interface Plan {
  id: string;
  name: string;
  price: string;
  features: string[];
  stripe_price_id: string | null;
}

const plans: Plan[] = [
  {
    id: 'free',
    name: 'Freeプラン',
    price: '¥0',
    features: [
      '月10回まで分析可能',
      '基本的なオッズ分析',
      '今日の試合閲覧',
    ],
    stripe_price_id: null,
  },
  {
    id: 'pro',
    name: 'Proプラン',
    price: '¥2,980/月',
    features: [
      '無制限の分析',
      '高度なオッズ分析',
      '今日の試合閲覧',
      'レーキバック設定',
      '優先サポート',
    ],
    stripe_price_id: 'price_1234567890',
  },
];

export default function SubscriptionPage() {
  const user = useAuthStore((state) => state.user);
  const router = useRouter();
  const [isLoading, setIsLoading] = useState<string | null>(null);
  const [error, setError] = useState('');

  const currentPlan = user?.role === 'user' ? 'free' : 'pro';

  const handleSubscribe = async (stripePriceId: string) => {
    setError('');
    setIsLoading('pro');

    try {
      const response = await apiClient.post<{ checkout_url: string }>('/subscribe', {
        stripe_price_id: stripePriceId,
      });
      router.push(`/dashboard/subscription/checkout?url=${encodeURIComponent(response.data.checkout_url)}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'サブスクリプション処理に失敗しました');
    } finally {
      setIsLoading(null);
    }
  };

  return (
    <div className="space-y-gap-lg">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-gray-900 mb-gap-sm">
          サブスクリプション
        </h1>
        <p className="text-muted">
          あなたに合ったプランを選択してください
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-danger-600 bg-opacity-10 p-gap-md">
          <p className="text-sm text-danger-600">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-gap-lg">
        {plans.map((plan) => {
          const isCurrent = plan.id === currentPlan;

          return (
            <Card
              key={plan.id}
              className={isCurrent ? 'ring-2 ring-primary-500' : ''}
            >
              <div className="space-y-gap-md">
                <div>
                  <h3 className="text-xl font-semibold tracking-tight text-gray-900">
                    {plan.name}
                  </h3>
                  {isCurrent && (
                    <span className="inline-block mt-gap-xs px-gap-sm py-gap-xs rounded-full text-xs font-medium bg-primary-500 text-white">
                      現在のプラン
                    </span>
                  )}
                </div>

                <div className="text-3xl font-semibold tracking-tight text-gray-900">
                  {plan.price}
                </div>

                <ul className="space-y-gap-sm">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-gap-sm">
                      <span className="text-success-600">✓</span>
                      <span className="text-sm text-gray-900">{feature}</span>
                    </li>
                  ))}
                </ul>

                {plan.id === 'pro' && !isCurrent && plan.stripe_price_id && (
                  <Button
                    onClick={() => handleSubscribe(plan.stripe_price_id!)}
                    isLoading={isLoading === 'pro'}
                    className="w-full focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    プランを選択
                  </Button>
                )}

                {isCurrent && (
                  <Button disabled className="w-full focus:outline-none focus:ring-2 focus:ring-primary-500">
                    利用中
                  </Button>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
