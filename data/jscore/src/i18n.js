/* 
==================================================================================================
  Jasy - JavaScript Tooling Refined
  Copyright 2010 Sebastian Werner
==================================================================================================
*/

(function(global)
{
  var translations = global.$$translation;
  
  
  var patch = function(msg, data, start)
  {
    // %1 = first, %2 = second, ...
    start = start == null ? -1 : start - 1;
    return msg.replace(/%([0-9])/g, function(match, pos) {
      return data[start+parseInt(pos)];
    });
  };
  
  // Export object
  global.i18n = 
  {
    /**
     * Applies the plural rule of the current locale and returns the 
     * field index on the translation data. This is the data used 
     * by the classical GNU gettext tools. See also:
     * http://www.gnu.org/software/hello/manual/gettext/Plural-forms.html
     *
     * @param nr {Number} Number to test
     * @return {String} One of 0, 1, 2, 3, 4, 5 or 6
     */    
    plural : (function(fields, Plural)
    {
      var code="", pos=0;
      var field, expr;

      for (var i=0; i<5; i++) 
      {
        field = fields[i];
        if (expr = Plural[fieldConst]) {
          code += "if(" + expr + ")return " + (pos++) + ";";
        }
      }
      
      code += "return " + pos + ";"
      
      return new Function("n", code);
    })(["ZERO", "ONE", "TWO", "FEW", "MANY"], locale.Plural),
    
    
    /**
     * Translates the given message and replaces placeholders in the result string.
     *
     * @param msg {String} Message to translate (used as a fallback when no translation is available)
     * @param varargs {...} Placeholder values
     * @return {String} Translated string
     */
    tr : function(msg, varargs)
    {
      var replacement = translations[msg] || msg;
      return arguments.length <= 1 ? replacement : patch(replacement, arguments, 1);
    },
    
    
    /**
     * Translates the given message (with a hint for the translator) and 
     * replaces placeholders in the result string.
     *
     * @param hint {String} Hint for the translator of the message
     * @param msg {String} Message to translate (used as a fallback when no translation is available)
     * @param varargs {...} Placeholder values
     * @return {String} Translated string
     */
    trc : function(hint, msg, varargs)
    {
      var replacement = translations[msg] || msg;
      return arguments.length <= 2 ? replacement : patch(replacement, arguments, 2);
    },
    
    
    /**
     * Translates the given message and replaces placeholders in the result string.
     *
     * @param msgSingular {String} Fallback message for singular case
     * @param msgPlural {String} Fallback message for plural case
     * @param number {Integer} Number of items (chooses between the exact translation which is being used)
     * @param varargs {...} Placeholder values
     * @return {String} Translated string
     */
    trn : function(msgSingular, msgPlural, number, varargs)
    {
      // Matching is based on singular "msgid"
      var replacement = translations[msgSingular];
      
      // Do numeric lookup
      if (typeof replacement == "object") {
        var result = replacement[i18n.plural(number)];
      }
      
      // Fallback to programmatically defined messages
      if (!result) {
        result = number == 1 ? msgSingular : msgPlural;
      }
      
      return arguments.length <= 3 ? result : patch(result, arguments, 3);
    }
  }
})(this);