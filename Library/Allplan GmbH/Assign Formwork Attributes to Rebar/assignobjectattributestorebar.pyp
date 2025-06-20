<?xml version="1.0" encoding="utf-8"?>
<Element>
	<Script>
		<Interactor>True</Interactor>
		<Title>Transfer Formwork Attributes to Rebar</Title>
		<Name>allplan_gmbh\assignattributes.py</Name>
		<Version>0.1</Version>
		<ReadLastInput>True</ReadLastInput>
	</Script>
	<Page>
		<Name>Start</Name>
		<Text>Start</Text>
		<TextId>1000</TextId>
		<Visible>True</Visible>
		<Enable>True</Enable>
		<Parameter>
			<Name>is_attribute_filter_visible</Name>
			<Text>1001</Text>
			<TextId>1001</TextId>
			<Value>1</Value>
			<ValueType>CheckBox</ValueType>
			<Visible>False</Visible>
		</Parameter>
		<Parameter>
			<Name>attributePicture</Name>
			<Value>attr.png</Value>
			<Orientation>Middle</Orientation>
			<ValueType>Picture</ValueType>
		</Parameter>
		<Parameter>
			<Name>Separator</Name>
			<ValueType>Separator</ValueType>
		</Parameter>
		<Parameter>
			<Name>ButtonRow</Name>
			<Text>Assign Attributes</Text>
			<TextId>1001</TextId>
			<ValueType>Row</ValueType>
			<Parameter>
				<Name>Button</Name>
				<Text>Do it now!</Text>
				<TextId>1002</TextId>
				<EventId>1</EventId>
				<ValueType>Button</ValueType>
			</Parameter>
		</Parameter>
		<Parameter>
			<Name>Row1</Name>
			<Text>1004</Text>
			<TextId>1004</TextId>
			<ValueType>Row</ValueType>
			<Value>OVERALL:1</Value>
			<Parameter>
				<Name>InfoPicture</Name>
				<Text>1005</Text>
				<TextId>1005</TextId>
				<Value>AllplanSettings.PictResPalette.eHotinfo</Value>
				<ValueType>Picture</ValueType>
			</Parameter>
			<Parameter>
				<Name>Tolerance</Name>
				<Text>Tolerance</Text>
				<TextId>1004</TextId>
				<Value>0.8</Value>
				<ValueType>Double</ValueType>
				<ValueSlider>True</ValueSlider>
				<MinValue>0</MinValue>
				<MaxValue>1.0</MaxValue>
				<IntervalValue>0.05</IntervalValue>
			</Parameter>
		</Parameter>
		<Parameter>
			<Name>Expander</Name>
			<Text>Expander</Text>
			<TextId>1003</TextId>
			<Value>False</Value>
			<ValueType>Expander</ValueType>
			<Visible>is_attribute_filter_visible</Visible>
			<Parameter>
				<Name>AttributeIDFilter</Name>
				<Text>Attributes</Text>
				<TextId>1003</TextId>
				<Value>[0]</Value>
				<Visible>is_attribute_filter_visible</Visible>
				<ValueType>AttributeId</ValueType>
				<ValueDialog>AttributeSelection</ValueDialog>
			</Parameter>
		</Parameter>

	</Page>
</Element>