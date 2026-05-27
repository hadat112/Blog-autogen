import * as React from "react";
import { cn } from "../../../lib/utils";
import { Card } from "../../../components/ui/Card";
import { Skeleton } from "../../../components/ui/Skeleton";

const AccountsSkeleton = () => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <Card key={i} className="p-6 h-48">
          <div className="flex justify-between items-start mb-4">
            <div className="space-y-2 w-full">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/4" />
            </div>
          </div>
          <div className="space-y-2 mt-8">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-5/6" />
          </div>
        </Card>
      ))}
    </div>
  );
};

export default AccountsSkeleton;
