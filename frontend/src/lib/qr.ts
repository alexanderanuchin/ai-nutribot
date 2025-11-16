import QRCode from 'qrcode'

export function generateQrDataUrl(value: string, options?: QRCode.QRCodeToDataURLOptions) {
  return QRCode.toDataURL(value, {
    errorCorrectionLevel: 'M',
    margin: 1,
    color: {
      dark: '#0f172a',
      light: '#ffffff',
    },
    ...options,
  })
}
