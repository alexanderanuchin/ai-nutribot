export function formatPhoneInput(value: string, previousValue = ''): string {
  let digits = value.replace(/\D/g, '');
  const prevDigits = previousValue.replace(/\D/g, '');

  const trimmed = value.trim();
  if (trimmed.startsWith('+7') || trimmed.startsWith('7') || trimmed.startsWith('8')) {
    digits = digits.slice(1);
  }

  if (previousValue && value.length < previousValue.length && digits.length === prevDigits.length) {
    digits = digits.slice(0, -1);
  }

  digits = digits.slice(0, 10);
  if (digits.length === 0) {
    return ['7', '8', '+7'].includes(value) ? '+7 (' : '';
  }

  let result = '+7 (' + digits.slice(0, 3);
  if (digits.length > 3) {
    result += ')';
  }
  if (digits.length > 3) {
    result += ' ' + digits.slice(3, 6);
  }
  if (digits.length > 6) {
    result += '-' + digits.slice(6, 8);
  }
  if (digits.length > 8) {
    result += '-' + digits.slice(8, 10);
  }
  return result;
}

export function normalizePhone(value: string): string {
  let digits = value.replace(/\D/g, '');

  if (digits.startsWith('8')) {
    digits = digits.slice(1);
  } else if (digits.startsWith('7') && digits.length > 10) {
    digits = digits.slice(1);
  } else if (digits.length > 10) {
    digits = digits.slice(-10);
  }

  digits = digits.slice(0, 10);
  if (digits.length === 0) return '';
  return '+7' + digits;
}