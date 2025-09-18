import React from 'react'

export default function Logo(){
  return (
    <svg
      className="nav-logo__svg"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 640 160"
      role="img"
      aria-labelledby="logoTitle logoDesc"
    >
      <title id="logoTitle">CaloIQ · баланс · здоровья</title>
      <desc id="logoDesc">
        Неоновая палитра на тёмном фоне (фон не заливается), хорошо смотрится в dark UI.
      </desc>
      <g transform="translate(40,14)">
        <path
          d="M72,20 C52,20 36,36 36,56 L48,56 C48,42 58,32 72,32 C86,32 96,42 96,56 L108,56 C108,36 92,20 72,20 Z"
          fill="#60A5FA"
        />
        <path
          d="M36,56 C24,56 16,68 16,84 C16,118 44,136 72,136 C100,136 128,118 128,84 C128,68 120,56 108,56 Z"
          fill="#60A5FA"
          opacity="0.18"
        />
        <path
          d="M28,92 L56,92 L64,76 L72,108 L80,84 L112,84"
          stroke="#60A5FA"
          strokeWidth="6"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        <path
          d="M36,56 C24,56 16,68 16,84 C16,118 44,136 72,136 C100,136 128,118 128,84 C128,68 120,56 108,56 Z"
          fill="none"
          stroke="#60A5FA"
          strokeWidth="6"
        />
      </g>
      <g transform="translate(200,102)">
        <text x="0" y="0" fontSize="68" fontWeight="800" fontFamily="Inter, 'SF Pro Display', Roboto, Helvetica, Arial, sans-serif">
          <tspan fill="#22D3EE">C</tspan>
          <tspan fill="#34D399">a</tspan>
          <tspan fill="#FBBF24">l</tspan>
          <tspan fill="#FB7185">o</tspan>
          <tspan fill="#60A5FA">IQ</tspan>
        </text>
        <text
          x="2"
          y="28"
          dy={10}
          fontSize="18"
          fill="#9CA3AF"
          opacity="0.95"
          letterSpacing="0.3em"
          fontFamily="Inter, 'SF Pro Display', Roboto, Helvetica, Arial, sans-serif"
        >
          баланс · здоровья
        </text>
      </g>
    </svg>
  )
}