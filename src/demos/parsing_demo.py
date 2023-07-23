from bs4 import BeautifulSoup
html_doc = '''
<div class="bbcode"><div class="well"><center><h2>Looking for GDs</h2><br><strong><span class="size-150">Ducky Chix - Prayer (Cut Ver.)</span></strong><br><br><span class="proportional-container js-gallery" style="width:860px;" data-width="860" data-height="280" data-index="0" data-gallery-id="796124545" data-src="https://i.ppy.sh/1e63e987713b820ea5282d6aa961cd65b6d26b6d/68747470733a2f2f6d656469612e646973636f72646170702e6e65742f6174746163686d656e74732f3736323733393535323532333132343733392f3738313935363931313339333830303231322f42657a5f6e617a77792d312e706e67"><span class="proportional-container__height" style="padding-bottom:32.558139534884%;"><img class="proportional-container__content" src="https://i.ppy.sh/1e63e987713b820ea5282d6aa961cd65b6d26b6d/68747470733a2f2f6d656469612e646973636f72646170702e6e65742f6174746163686d656e74732f3736323733393535323532333132343733392f3738313935363931313339333830303231322f42657a5f6e617a77792d312e706e67" alt=""></span></span><br></center></div><center><br><strong><span class="size-150">Hello!</span></strong><br><br>I'm looking for some GDs to my new project. If you want to make one write under this topic. I will appreciate any help. <br><br><strong><span class="size-150"><em><a rel="nofollow" href="https://osu.ppy.sh/beatmapsets/1310416#osu/2716393">Link</a></em></span></strong></center><br><div class="well"><center><strong></strong><h2><strong>Difficulties:</strong></h2><strong></strong><br><span class="proportional-container js-gallery" style="width:16px;" data-width="16" data-height="16" data-index="1" data-gallery-id="796124545" data-src="https://i.ppy.sh/e04f0284d80f408496c3ab151c71902be9978cbd/68747470733a2f2f6f73752e7070792e73682f68656c702f77696b692f7368617265642f646966662f656173792d732e706e67"><span class="proportional-container__height" style="padding-bottom:100%;"><img class="proportional-container__content" src="https://i.ppy.sh/e04f0284d80f408496c3ab151c71902be9978cbd/68747470733a2f2f6f73752e7070792e73682f68656c702f77696b692f7368617265642f646966662f656173792d732e706e67" alt=""></span></span> <strong>Easy</strong> - Looking for GD<br><span class="proportional-container js-gallery" style="width:16px;" data-width="16" data-height="16" data-index="2" data-gallery-id="796124545" data-src="https://i.ppy.sh/d87f06527a3514beb5d361a0e7f2f76cd7dbd4ae/68747470733a2f2f6f73752e7070792e73682f68656c702f77696b692f7368617265642f646966662f6e6f726d616c2d732e706e67"><span class="proportional-container__height" style="padding-bottom:100%;"><img class="proportional-container__content" src="https://i.ppy.sh/d87f06527a3514beb5d361a0e7f2f76cd7dbd4ae/68747470733a2f2f6f73752e7070792e73682f68656c702f77696b692f7368617265642f646966662f6e6f726d616c2d732e706e67" alt=""></span></span> <strong>Normal</strong> - Looking for GD<br><span class="proportional-container js-gallery" style="width:16px;" data-width="16" data-height="16" data-index="3" data-gallery-id="796124545" data-src="https://i.ppy.sh/f8460f6be7fe5cc4fa65a783212345a96aadb926/68747470733a2f2f6f73752e7070792e73682f68656c702f77696b692f7368617265642f646966662f686172642d732e706e67"><span class="proportional-container__height" style="padding-bottom:100%;"><img class="proportional-container__content" src="https://i.ppy.sh/f8460f6be7fe5cc4fa65a783212345a96aadb926/68747470733a2f2f6f73752e7070792e73682f68656c702f77696b692f7368617265642f646966662f686172642d732e706e67" alt=""></span></span> <strong>Hard</strong> - Looking for GD<br><span class="proportional-container js-gallery" style="width:16px;" data-width="16" data-height="16" data-index="4" data-gallery-id="796124545" data-src="https://i.ppy.sh/cbe62f5fb1a4589728117720394bdc81d701829c/68747470733a2f2f6f73752e7070792e73682f68656c702f77696b692f7368617265642f646966662f696e73616e652d732e706e67"><span class="proportional-container__height" style="padding-bottom:100%;"><img class="proportional-container__content" src="https://i.ppy.sh/cbe62f5fb1a4589728117720394bdc81d701829c/68747470733a2f2f6f73752e7070792e73682f68656c702f77696b692f7368617265642f646966662f696e73616e652d732e706e67" alt=""></span></span> <strong>Light Insane</strong> - Looking for GD<br><span class="proportional-container js-gallery" style="width:16px;" data-width="16" data-height="16" data-index="4" data-gallery-id="796124545" data-src="https://i.ppy.sh/cbe62f5fb1a4589728117720394bdc81d701829c/68747470733a2f2f6f73752e7070792e73682f68656c702f77696b692f7368617265642f646966662f696e73616e652d732e706e67"><span class="proportional-container__height" style="padding-bottom:100%;"><img class="proportional-container__content" src="https://i.ppy.sh/cbe62f5fb1a4589728117720394bdc81d701829c/68747470733a2f2f6f73752e7070792e73682f68656c702f77696b692f7368617265642f646966662f696e73616e652d732e706e67" alt=""></span></span> <strong>Insane</strong> - Done<br><br><span class="proportional-container js-gallery" style="width:16px;" data-width="16" data-height="16" data-index="6" data-gallery-id="796124545" data-src="https://i.ppy.sh/a2d458fb8e7cf47de92909c581fe588fe6a53472/68747470733a2f2f692e696d6775722e636f6d2f4749426b3536312e706e67"><span class="proportional-container__height" style="padding-bottom:100%;"><img class="proportional-container__content" src="https://i.ppy.sh/a2d458fb8e7cf47de92909c581fe588fe6a53472/68747470733a2f2f692e696d6775722e636f6d2f4749426b3536312e706e67" alt=""></span></span> <strong>Hitsounds</strong> - Done (but if someone want to make better ones i will add them)<br></center></div></div>
'''

html_doc = html_doc.replace('\n', '')
root = BeautifulSoup(html_doc, 'lxml')
nl = '\n'

for tag in root.find_all(True):
    if tag.name == 'li':
        tag.insert_before('    • ')
        continue
    
    if tag.name == 'a':
        tag.replace_with(f'[{tag.text}]({tag["href"]})')
        continue
    
    if tag.name == 'img':
        try:
            if 'smiley' in tag['class']: 
                tag.replace_with(':smile:')
            else:
                tag.replace_with(f'\n> [img]({tag["src"]})')
                continue
        except:
            continue
    
    if tag.name == 'br':
        tag.replace_with('\n')
        continue

    if tag.name == 'del':
        tag.insert_before('~~')
        tag.insert_after('~~')
        continue
    
    if tag.name == 'strong':
        tag.insert_before('**')
        tag.insert_after('**')
        continue

# Keeps just the "<username> wrote:" part
for tag in root.find_all(True):
    if tag.name == 'blockquote':
        for tag_h4 in tag.find('h4'):
            tag.replace_with(f'> **{tag_h4.string}** [...]\n\n')


print(str(root.text).strip())