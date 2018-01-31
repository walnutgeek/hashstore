import _ from 'lodash'

export class IntEnum {
    constructor(s2i,methods){
        this.s2i = s2i;
        this.i2s = _.invert(s2i);
        _.forOwn(s2i, (v,k)=> this[k] = k);
        if(methods){
            _.forOwn(methods,(fn,fnName)=> this[fnName] = fn);
        }

    }

    keys(){
        return Object.keys(this.s2i);
    }

    values(){
        return Object.keys(this.i2s);
    }

}

export class ValueEnum {
    constructor(k2v, methods){
        this.k2v = k2v;
        _.forOwn(k2v,(v,k)=> {
            this.k2v[k].k = k;
            this[k] = k;
        });
        if(methods){
            _.forOwn(methods,(fn,k)=> this[k] = fn);
        }
    }

    keys(){
        return Object.keys(this.k2v);
    }

    value(key){
        return this.k2v[key];
    }

}