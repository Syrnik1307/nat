import React from 'react';

const EmptyState = ({ icon, title, description, action }) => {
  return (
    <div className="flex flex-col items-center text-center py-16 gap-4">
      <div className="relative">
        <div className="rounded-full bg-indigo-50 text-indigo-600 p-6 shadow-sm transition-transform duration-200 hover:-translate-y-1">
          <div className="text-4xl" aria-hidden="true">{icon}</div>
        </div>
      </div>
      <div className="max-w-xl flex flex-col gap-2">
        <h3 className="text-lg font-semibold text-slate-800 font-[Plus_Jakarta_Sans]">{title}</h3>
        <p className="text-slate-500 font-[Plus_Jakarta_Sans] leading-relaxed">{description}</p>
      </div>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
};

export default EmptyState;
