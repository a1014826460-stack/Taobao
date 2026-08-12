function Person(name) {
  this.name = name;
}
Person.prototype.sayHello = function() {
  console.log(`Hello, I'm ${this.name}`);
};

const alice = new Person('Alice');

// 属性查找过程：
alice.sayHello(); // alice 自身没有 sayHello，沿着 __proto__ 找到 Person.prototype，调用成功
alice.toString(); // Person.prototype 没有 toString，继续沿着 Person.prototype.__proto__ 找到 Object.prototype，调用成功

// 查看原型链：
console.log(alice.__proto__ === Person.prototype);   // true
console.log(Person.prototype.__proto__ === Object.prototype); // true
console.log(Object.prototype.__proto__); // null