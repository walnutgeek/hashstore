import factory from 'base-x';

export const base62 = factory(  '0123456789' +
                                'abcdefghijklmnopqrstuvwxyz' +
                                'ABCDEFGHIJKLMNOPQRSTUVWXYZ');

import {IntEnum} from './enums';

export const KeyStructure = new IntEnum({
    INLINE: 0,
    SHA256: 1,
    GUID256: 2,
    TINYNAME: 3
});

export const DataType = new IntEnum({
    UNCATEGORIZED: 0,
    BUNDLE: 1,
});


export default class Cake{
    constructor(s){
        this.s = s;
        const buf = base62.decode(s);
        const header = buf[0];
        this.keyStructure = KeyStructure.i2s[header & 0x0F];
        this.dataType = DataType.i2s[header>>4];
        this.data = buf.slice(1);
    }


    static ensureCake(s){
        if( !s || s === "null" || s === "None" ){
            return null;
        }
        return new Cake(s);
    }

    short(){
        return this.s.length > 8 ? '#'+ this.s.substring(this.s.length-8) : this.s ;
    }


    has_data(){
        return this.keyStructure === KeyStructure.INLINE;
    }

    toString(){
        return this.s;
    }
}

