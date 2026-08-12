function getChain(o) {
  var chain = [];
  while(o) {
    chain.push(o.constructor ? o.constructor.name : 'null');
    o = Object.getPrototypeOf(o);
  }
  return chain;
}
var c = document.createElement('canvas');
console.log('canvas chain:', getChain(c).join(' -> '));
console.log('canvas toString:', Object.prototype.toString.call(c));
var ctx = c.getContext('2d');
console.log('ctx chain:', getChain(ctx).join(' -> '));
console.log('ctx toString:', Object.prototype.toString.call(ctx));
var gl = c.getContext('webgl');
console.log('gl chain:', getChain(gl).join(' -> '));
console.log('gl toString:', Object.prototype.toString.call(gl));
