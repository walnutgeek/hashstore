import {Cake,CakePath} from './Cake';
import {TextEncoder,TextDecoder} from 'text-encoding';

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

test('EncoderDecoder', ()=>{
  var uint8array = new TextEncoder("utf-8").encode("¢");
  expect(uint8array).toEqual(new Uint8Array([194, 162]))
  var string = new TextDecoder("utf-8").decode(uint8array);
  expect(string).toBe("¢");
});

test('CakePath', ()=>{
    // >>> root = CakePath('/2EibTlogc1l8Qo9JCJXHTW0hD0h7Se9')
    // >>> root
    let root = new CakePath('/2EibTlogc1l8Qo9JCJXHTW0hD0h7Se9');
    expect(root.root).toEqual(new Cake('2EibTlogc1l8Qo9JCJXHTW0hD0h7Se9'));
    expect(root.path).toEqual([]);
    expect(root.toString()).toBe('/2EibTlogc1l8Qo9JCJXHTW0hD0h7Se9');
    root = new CakePath('/2EibTlogc1l8Qo9JCJXHTW0hD0h7Se9/');
    expect(root.root).toEqual(new Cake('2EibTlogc1l8Qo9JCJXHTW0hD0h7Se9'));
    expect(root.path).toEqual([]);
    expect(root.toString()).toBe('/2EibTlogc1l8Qo9JCJXHTW0hD0h7Se9');
    // >>> absolute = CakePath('/2EibTlogc1l8Qo9JCJXHTW0hD0h7Se9/b.txt')
    // >>> absolute
    // CakePath('/2EibTlogc1l8Qo9JCJXHTW0hD0h7Se9/b.txt')
    let absolute = new CakePath('/2EibTlogc1l8Qo9JCJXHTW0hD0h7Se9/b.txt');
    expect(absolute.toString()).toBe('/2EibTlogc1l8Qo9JCJXHTW0hD0h7Se9/b.txt');
    // >>> relative = CakePath('y/z')
    // >>> relative
    // CakePath('y/z')
    let relative = new CakePath('y/z');
    expect(relative.toString()).toBe('y/z')
});
