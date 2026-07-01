# Install

    pip install -U git+https://github.com/mayank31313/python-dependency-injection.git

# Documentation

Documentation is shifted [here](https://mayank31313.github.io/get-started/site/python-di/)


# Example    
Follow the below code to simplify understanding, or can also refer to [main.py](main.py)
    
    from cndi.annotations import Bean, Autowired, AppInitializer
    
    class BeanTest:
        def __init__(self, name):
            self.name = name
    
    
    @Bean()
    def getTestBean() -> BeanTest:
        return BeanTest("Test 123")
    
    testBean = None
    
    app = AppInitializer()
    if __name__ == "__main__":
        @Autowired()
        def setTestBean(bean: BeanTest):
            global testBean
            testBean = bean
    
        app.run()
    
        print(testBean.name)
