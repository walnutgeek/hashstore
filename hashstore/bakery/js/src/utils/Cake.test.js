import {Cake,CakePath} from './Cake';
import {TextEncoder,TextDecoder} from 'text-encoding';

test('Cake', () => {
  let inline_cake = new Cake('01aMUQDApalaaYbXFjBVMMvyCAMfSPcTojI0745igi');
  expect(inline_cake.has_data()).toBe(true);
  expect(inline_cake.keyStructure).toBe("INLINE");
  expect(inline_cake.role).toBe("SYNAPSE");
  expect(inline_cake.data.toString('utf-8')).toBe("The quick brown fox jumps over");
  let longer_cake = new Cake('3RSFSb2Kdm05KBWAQ5RHM5B0d49DsaZHlY5eO9XkAcWM');
  expect(longer_cake.keyStructure).toBe("SHA256");
  expect(longer_cake.role).toBe("NEURON");
  expect(longer_cake.data.length).toBe(32);
  longer_cake = new Cake('5vJTH93SapJAY88AZ5kRwqXAhEsjxwKpQT7Z0AaWVyDR');
  expect(longer_cake.keyStructure).toBe("PORTAL");
  expect(longer_cake.role).toBe("NEURON");
  expect(longer_cake.data.length).toBe(32);
});

test('EncoderDecoder', ()=>{
  var uint8array = new TextEncoder("utf-8").encode("¢");
  expect(uint8array).toEqual(new Uint8Array([194, 162]))
  var string = new TextDecoder("utf-8").decode(uint8array);
  expect(string).toBe("¢");
});

test('CakePath', ()=>{
    // >>> root = CakePath('/kNfTUQyhOKGv7f6uIAsv5tmLStjCjvL')
    // >>> root
    let root = new CakePath('/dCYNBHoPFLCwpVdQU5LhiF0i6U60KF');
    expect(root.root).toEqual(new Cake('dCYNBHoPFLCwpVdQU5LhiF0i6U60KF'));
    expect(root.path).toEqual([]);
    expect(root.toString()).toBe('/dCYNBHoPFLCwpVdQU5LhiF0i6U60KF');
    expect(root.root.role).toEqual("NEURON");
    expect(root.root.keyStructure).toBe("INLINE");
    expect(root.root.data.toString('utf-8')).toBe('[["b.text"], ["06wO"]]');

    root = new CakePath('/dCYNBHoPFLCwpVdQU5LhiF0i6U60KF/');
    expect(root.root).toEqual(new Cake('dCYNBHoPFLCwpVdQU5LhiF0i6U60KF'));
    expect(root.path).toEqual([]);
    expect(root.toString()).toBe('/dCYNBHoPFLCwpVdQU5LhiF0i6U60KF');
    // >>> absolute = CakePath('/kNfTUQyhOKGv7f6uIAsv5tmLStjCjvL/b.txt')
    // >>> absolute
    // CakePath('/kNfTUQyhOKGv7f6uIAsv5tmLStjCjvL/b.txt')
    let absolute = new CakePath('/dCYNBHoPFLCwpVdQU5LhiF0i6U60KF/b.txt');
    expect(absolute.toString()).toBe('/dCYNBHoPFLCwpVdQU5LhiF0i6U60KF/b.txt');
    // >>> relative = CakePath('y/z')
    // >>> relative
    // CakePath('y/z')
    let relative = new CakePath('y/z');
    expect(relative.toString()).toBe('y/z')
});
