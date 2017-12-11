import Cake from './Cake';

test('Cake', () => {
  let inline_cake = new Cake('01aMUQDApalaaYbXFjBVMMvyCAMfSPcTojI0745igi');
  expect(inline_cake.has_data()).toBe(true);
  expect(inline_cake.keyStructure).toBe("INLINE");
  expect(inline_cake.data.toString('utf-8')).toBe("The quick brown fox jumps over");
  let longer_cake = new Cake('1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV');
  expect(longer_cake.keyStructure).toBe("SHA256");
  expect(longer_cake.dataType).toBe("UNCATEGORIZED");
  expect(longer_cake.data.length).toBe(32);
});