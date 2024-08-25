


var lexBaabnq = (raw) => {

    //state
    var isString  = false;
    var isComment = false;

    var tokenStream = [];
    var buffer = "";

    var index = 0;
    var tokenStartIndex = 0;

    let getTokenType = (content) => {
        let EOS = ";";
        if (content == EOS) return { categ : "EOS"  , style : "color: gray" };        
        
        let OP = ["+", "-", "|", "&", "^", "<<", ">>", "=", "~", "==", "!=", "<", ">", "(", ")"];
        
        if (/^\d+$/.test(content))   return { categ : "NUM", style : "color: orange" };
        if (content.startsWith("_")) return { categ : "VAR", style : "color: cyan" };
        if (content.startsWith("'")) return { categ : "STR", style : "color: orange" };
        if (OP.includes(content))    return { categ : "OP" , style : "color: red" };
        if (content.startsWith('"')) return { categ : "CMT", style : "color: gray" };
        
        let GENERIC_COMMANDS = ["put", "use", "putchr", "print", "input", "asm"];
        let FLOWCTL_COMMANDS = ["lab", "jump"];
        let STACKIO_COMMANDS = ["push", "pull", "sub", "return"];
        let MEMORY__COMMANDS = ["static", "new", "free", "<-", "->"];
        
        
        if (GENERIC_COMMANDS.includes(content)) return { categ : "GEN_COM", style : "color: #2f2" }
        if (FLOWCTL_COMMANDS.includes(content)) return { categ : "FLW_COM", style : "color: #ff0" }
        if (STACKIO_COMMANDS.includes(content)) return { categ : "STK_COM", style : "color: #f0f" }
        if (MEMORY__COMMANDS.includes(content)) return { categ : "STK_COM", style : "color: #88f" }

        return { categ : "WORD", style : "color: #fff" };
    }
    

    let pushChar = (chr) => tokenStream.push({ 
        content : ";", 
        start : index, 
        end : index + 1, 
        type : getTokenType(chr)
    }); 

    let pushBuffer = () => {
        tokenStream.push({
            content : buffer,
            start : tokenStartIndex,
            end : index,
            type : getTokenType(buffer),
        });
        buffer = "";
    };
    
    let updateTokenStart = () => tokenStartIndex = index + 1;

    for (let chr of raw) {
        /**/ if (isString  && chr != '\'') buffer += chr;
        else if (isComment && chr != '\n') buffer += chr;
        else switch (chr)
        {
            case ';':
            case '(':
            case ')':
                if (buffer) pushBuffer();
                pushChar(chr);
                updateTokenStart();
                break;
                                
            case '\n':
                isComment = false;

            case ' ':
                if (buffer) pushBuffer();
                updateTokenStart();
                break;
                
            case '"':
                isComment = true;
                buffer = '"';
                break; 

            case '\'':                
                isString = !isString;
                buffer = '\'';
                break;
         
            default:                
                buffer += chr;
                break;
        }
        
        index++;
    }
    
    console.log(tokenStream);
    return tokenStream;
};






var insert = (str, index, payload) => str.substr(0, index) + payload + str.substr(index);



// for checking if content of tag actually changed
var tagContentMapper = {};


var applyHighlightTokensToTag = (tag, tokenStream) => {
    let contedit = tag.isContentEditable;

    let content = tag.innerText;
    for (let token of tokenStream.reverse()) {
        let end   = token.end;
        let start = token.start;
        let style = token.type.style;

        content = insert(insert(content, end, "</span>"), start, `<span contenteditable=${contedit} style="${style}">`);
    }
    
    tag.innerHTML = content;
};



var updateHighlighTag = (tag) => {
    
    let tokenStream = lexBaabnq(tag.innerText);    
    applyHighlightTokensToTag(tag, tokenStream);
        
};


var highlighInit = () => {
    var tags = document.getElementsByClassName("baabnq-source");    

    let handleInputEvent = event => updateHighlighTag(event.target);

    // highlight all
    for (let tag of tags) updateHighlighTag(tag);
        
    //register
    for (let tag of tags) tag.addEventListener("focusout", handleInputEvent);
}


window.addEventListener("load", highlighInit);



