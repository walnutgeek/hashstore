import React from 'react';

const toHex=(pad,v)=>(
    (pad+v.toString(16)).substr(-pad.length));

const Raw = {
    render({content}) {
        const binary = new Uint8Array(content);
        const all_ascii = binary.every(c=>c<128);
        if(all_ascii) {
            content = String.fromCharCode.apply(null,binary);
        }else{
            let s = '';
            const l = binary.length;
            const addrPadding = '0'.repeat(l.toString(16).length + 1);
            for(let i = 0 ; i < l ; i+=16 ){
                s += toHex(addrPadding,i);
                s += ': ';
                let ascii = '| ';
                for( let j = 0 ; j < 16 ; j++){
                    if( i+j < l ){
                        let chCode = binary[i+j];
                        s+= toHex("00", chCode);
                        s+= ' ';
                        ascii += (chCode >=32 && chCode < 128) ?
                            String.fromCharCode(chCode) : '.';
                    }else{
                        s+='   ';
                    }
                }
                s+= ascii + '\n';
            }
            content = s;
        }
        return <pre>{content}</pre>;
    }
};
export default Raw;
