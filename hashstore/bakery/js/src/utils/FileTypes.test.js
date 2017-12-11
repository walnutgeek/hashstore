import FileTypes from './FileTypes';


test('FileTypes', () => {
  expect(FileTypes.findByExt('Jpeg')).toBe('JPG');
  expect(FileTypes.findByExt('hsb')).toBe('HSB');
  expect(FileTypes.mime('HSB')).toBe('text/hsb')
  expect(FileTypes.k2v.WDF.mime).toBe('text/wdf')
});